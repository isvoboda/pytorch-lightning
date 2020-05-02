import platform

import pytest
import torch
from torch.utils.data.dataloader import DataLoader
from torch.utils.data.dataset import Subset

import tests.base.utils as tutils
from pytorch_lightning import Trainer
from pytorch_lightning.utilities.exceptions import MisconfigurationException
from tests.base import (
    TestModelBase,
    LightningTestModel,
    LightEmptyTestStep,
    LightValidationMultipleDataloadersMixin,
    LightTestMultipleDataloadersMixin,
    LightTestFitSingleTestDataloadersMixin,
    LightTestFitMultipleTestDataloadersMixin,
    LightValStepFitMultipleDataloadersMixin,
    LightValStepFitSingleDataloaderMixin,
    LightTrainDataloader,
    LightInfTrainDataloader,
    LightInfValDataloader,
    LightInfTestDataloader,
    LightZeroLenDataloader
)


@pytest.mark.parametrize("dataloader_options", [
    dict(train_percent_check=-0.1),
    dict(train_percent_check=1.1),
    dict(val_check_interval=1.1),
    dict(val_check_interval=10000),
])
def test_dataloader_config_errors(tmpdir, dataloader_options):

    class CurrentTestModel(
        LightTrainDataloader,
        TestModelBase,
    ):
        pass

    hparams = tutils.get_default_hparams()
    model = CurrentTestModel(hparams)

    # fit model
    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=1,
        **dataloader_options,
    )

    with pytest.raises(ValueError):
        trainer.fit(model)


def test_multiple_val_dataloader(tmpdir):
    """Verify multiple val_dataloader."""

    class CurrentTestModel(
        LightTrainDataloader,
        LightValidationMultipleDataloadersMixin,
        TestModelBase,
    ):
        pass

    hparams = tutils.get_default_hparams()
    model = CurrentTestModel(hparams)

    # fit model
    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=1,
        val_percent_check=0.1,
        train_percent_check=1.0,
    )
    result = trainer.fit(model)

    # verify training completed
    assert result == 1

    # verify there are 2 val loaders
    assert len(trainer.val_dataloaders) == 2, \
        'Multiple val_dataloaders not initiated properly'

    # make sure predictions are good for each val set
    for dataloader in trainer.val_dataloaders:
        tutils.run_prediction(dataloader, trainer.model)


def test_multiple_test_dataloader(tmpdir):
    """Verify multiple test_dataloader."""

    class CurrentTestModel(
        LightTrainDataloader,
        LightTestMultipleDataloadersMixin,
        LightEmptyTestStep,
        TestModelBase,
    ):
        pass

    hparams = tutils.get_default_hparams()
    model = CurrentTestModel(hparams)

    # fit model
    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=1,
        val_percent_check=0.1,
        train_percent_check=0.2
    )
    trainer.fit(model)
    trainer.test()

    # verify there are 2 val loaders
    assert len(trainer.test_dataloaders) == 2, \
        'Multiple test_dataloaders not initiated properly'

    # make sure predictions are good for each test set
    for dataloader in trainer.test_dataloaders:
        tutils.run_prediction(dataloader, trainer.model)

    # run the test method
    trainer.test()


def test_train_dataloaders_passed_to_fit(tmpdir):
    """Verify that train dataloader can be passed to fit """

    class CurrentTestModel(LightTrainDataloader, TestModelBase):
        pass

    hparams = tutils.get_default_hparams()

    # only train passed to fit
    model = CurrentTestModel(hparams)
    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=1,
        val_percent_check=0.1,
        train_percent_check=0.2
    )
    result = trainer.fit(model, train_dataloader=model._dataloader(train=True))

    assert result == 1


def test_train_val_dataloaders_passed_to_fit(tmpdir):
    """ Verify that train & val dataloader can be passed to fit """

    class CurrentTestModel(
        LightTrainDataloader,
        LightValStepFitSingleDataloaderMixin,
        TestModelBase,
    ):
        pass

    hparams = tutils.get_default_hparams()

    # train, val passed to fit
    model = CurrentTestModel(hparams)
    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=1,
        val_percent_check=0.1,
        train_percent_check=0.2
    )
    result = trainer.fit(model,
                         train_dataloader=model._dataloader(train=True),
                         val_dataloaders=model._dataloader(train=False))
    assert result == 1
    assert len(trainer.val_dataloaders) == 1, \
        f'`val_dataloaders` not initiated properly, got {trainer.val_dataloaders}'


def test_all_dataloaders_passed_to_fit(tmpdir):
    """Verify train, val & test dataloader can be passed to fit """

    class CurrentTestModel(
        LightTrainDataloader,
        LightValStepFitSingleDataloaderMixin,
        LightTestFitSingleTestDataloadersMixin,
        LightEmptyTestStep,
        TestModelBase,
    ):
        pass

    hparams = tutils.get_default_hparams()

    # train, val and test passed to fit
    model = CurrentTestModel(hparams)
    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=1,
        val_percent_check=0.1,
        train_percent_check=0.2
    )

    result = trainer.fit(model,
                         train_dataloader=model._dataloader(train=True),
                         val_dataloaders=model._dataloader(train=False))

    trainer.test(test_dataloaders=model._dataloader(train=False))

    assert result == 1
    assert len(trainer.val_dataloaders) == 1, \
        f'val_dataloaders` not initiated properly, got {trainer.val_dataloaders}'
    assert len(trainer.test_dataloaders) == 1, \
        f'test_dataloaders` not initiated properly, got {trainer.test_dataloaders}'


def test_multiple_dataloaders_passed_to_fit(tmpdir):
    """Verify that multiple val & test dataloaders can be passed to fit."""

    class CurrentTestModel(
        LightningTestModel,
        LightValStepFitMultipleDataloadersMixin,
        LightTestFitMultipleTestDataloadersMixin,
    ):
        pass

    hparams = tutils.get_default_hparams()

    # train, multiple val and multiple test passed to fit
    model = CurrentTestModel(hparams)
    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=1,
        val_percent_check=0.1,
        train_percent_check=0.2
    )

    results = trainer.fit(
        model,
        train_dataloader=model._dataloader(train=True),
        val_dataloaders=[model._dataloader(train=False), model._dataloader(train=False)],
    )
    assert results

    trainer.test(test_dataloaders=[model._dataloader(train=False), model._dataloader(train=False)])

    assert len(trainer.val_dataloaders) == 2, \
        f'Multiple `val_dataloaders` not initiated properly, got {trainer.val_dataloaders}'
    assert len(trainer.test_dataloaders) == 2, \
        f'Multiple `test_dataloaders` not initiated properly, got {trainer.test_dataloaders}'


def test_mixing_of_dataloader_options(tmpdir):
    """Verify that dataloaders can be passed to fit"""

    class CurrentTestModel(
        LightTrainDataloader,
        LightValStepFitSingleDataloaderMixin,
        LightTestFitSingleTestDataloadersMixin,
        TestModelBase,
    ):
        pass

    hparams = tutils.get_default_hparams()
    model = CurrentTestModel(hparams)

    trainer_options = dict(
        default_root_dir=tmpdir,
        max_epochs=1,
        val_percent_check=0.1,
        train_percent_check=0.2
    )

    # fit model
    trainer = Trainer(**trainer_options)
    fit_options = dict(val_dataloaders=model._dataloader(train=False))
    results = trainer.fit(model, **fit_options)
    assert results

    # fit model
    trainer = Trainer(**trainer_options)
    fit_options = dict(val_dataloaders=model._dataloader(train=False))
    test_options = dict(test_dataloaders=model._dataloader(train=False))

    _ = trainer.fit(model, **fit_options)
    trainer.test(**test_options)

    assert len(trainer.val_dataloaders) == 1, \
        f'`val_dataloaders` not initiated properly, got {trainer.val_dataloaders}'
    assert len(trainer.test_dataloaders) == 1, \
        f'`test_dataloaders` not initiated properly, got {trainer.test_dataloaders}'


def test_inf_train_dataloader(tmpdir):
    """Test inf train data loader (e.g. IterableDataset)"""

    class CurrentTestModel(
        LightInfTrainDataloader,
        LightningTestModel
    ):
        pass

    hparams = tutils.get_default_hparams()
    model = CurrentTestModel(hparams)

    # fit model
    with pytest.raises(MisconfigurationException):
        trainer = Trainer(
            default_root_dir=tmpdir,
            max_epochs=1,
            val_check_interval=0.5
        )
        trainer.fit(model)

    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=1,
        val_check_interval=50
    )
    result = trainer.fit(model)

    # verify training completed
    assert result == 1

    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=1
    )
    result = trainer.fit(model)

    # verify training completed
    assert result == 1


def test_inf_val_dataloader(tmpdir):
    """Test inf val data loader (e.g. IterableDataset)"""

    class CurrentTestModel(
        LightInfValDataloader,
        LightningTestModel
    ):
        pass

    hparams = tutils.get_default_hparams()
    model = CurrentTestModel(hparams)

    # fit model
    with pytest.raises(MisconfigurationException):
        trainer = Trainer(
            default_root_dir=tmpdir,
            max_epochs=1,
            val_percent_check=0.5
        )
        trainer.fit(model)

    # logger file to get meta
    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=1
    )
    result = trainer.fit(model)

    # verify training completed
    assert result == 1


def test_inf_test_dataloader(tmpdir):
    """Test inf test data loader (e.g. IterableDataset)"""

    class CurrentTestModel(
        LightInfTestDataloader,
        LightningTestModel,
        LightTestFitSingleTestDataloadersMixin
    ):
        pass

    hparams = tutils.get_default_hparams()
    model = CurrentTestModel(hparams)

    # fit model
    with pytest.raises(MisconfigurationException):
        trainer = Trainer(
            default_root_dir=tmpdir,
            max_epochs=1,
            test_percent_check=0.5
        )
        trainer.test(model)

    # logger file to get meta
    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=1
    )
    result = trainer.fit(model)
    trainer.test(model)

    # verify training completed
    assert result == 1


def test_error_on_zero_len_dataloader(tmpdir):
    """ Test that error is raised if a zero-length dataloader is defined """

    class CurrentTestModel(
        LightZeroLenDataloader,
        LightningTestModel
    ):
        pass

    hparams = tutils.get_default_hparams()
    model = CurrentTestModel(hparams)

    # fit model
    with pytest.raises(ValueError):
        trainer = Trainer(
            default_root_dir=tmpdir,
            max_epochs=1,
            test_percent_check=0.5
        )
        trainer.fit(model)


@pytest.mark.skipif(platform.system() == 'Windows', reason='Does not apply to Windows platform.')
def test_warning_with_few_workers(tmpdir):
    """ Test that error is raised if dataloader with only a few workers is used """

    class CurrentTestModel(
        LightTrainDataloader,
        LightValStepFitSingleDataloaderMixin,
        LightTestFitSingleTestDataloadersMixin,
        LightEmptyTestStep,
        TestModelBase,
    ):
        pass

    hparams = tutils.get_default_hparams()
    model = CurrentTestModel(hparams)

    fit_options = dict(train_dataloader=model._dataloader(train=True),
                       val_dataloaders=model._dataloader(train=False))
    test_options = dict(test_dataloaders=model._dataloader(train=False))

    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=1,
        val_percent_check=0.1,
        train_percent_check=0.2
    )

    # fit model
    with pytest.warns(UserWarning, match='train'):
        trainer.fit(model, **fit_options)

    with pytest.warns(UserWarning, match='val'):
        trainer.fit(model, **fit_options)

    with pytest.warns(UserWarning, match='test'):
        trainer.test(**test_options)


@pytest.mark.skipif(torch.cuda.device_count() < 2, reason='Test requires multiple GPUs')
def test_dataloader_reinit_for_subclass():

    class CustomDataLoader(torch.utils.data.DataLoader):
        def __init__(self, dataset, batch_size=1, shuffle=False, sampler=None,
                     batch_sampler=None, num_workers=0, collate_fn=None,
                     pin_memory=False, drop_last=False, timeout=0,
                     worker_init_fn=None, dummy_kwarg=None):
            super().__init__(dataset, batch_size, shuffle, sampler, batch_sampler,
                             num_workers, collate_fn, pin_memory, drop_last, timeout,
                             worker_init_fn)

            self.dummy_kwarg = dummy_kwarg

    trainer = Trainer(
        gpus=[0, 1],
        num_nodes=1,
        distributed_backend='ddp',
    )

    class CustomDummyObj:
        sampler = None

    result = trainer.auto_add_sampler(CustomDummyObj(), train=True)
    assert isinstance(result, CustomDummyObj), "Wrongly reinstantiated data loader"

    result = trainer.auto_add_sampler(CustomDataLoader(list(range(1000))), train=True)
    assert isinstance(result, torch.utils.data.DataLoader)
    assert isinstance(result, CustomDataLoader)
    assert hasattr(result, 'dummy_kwarg')


@pytest.mark.skipif(torch.cuda.device_count() < 3, reason='Test requires multiple GPUs')
def test_batch_size_smaller_than_num_gpus():
    # we need at least 3 gpus for this test
    num_gpus = 3
    batch_size = 3

    class CurrentTestModel(
        LightTrainDataloader,
        TestModelBase,
    ):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.c_d1_bn = torch.nn.ReLU()

        def train_dataloader(self):
            dataloader = super().train_dataloader()
            # construct a dataset with a size that is not divisible by num_gpus
            # therefore the last batch will have a size < num_gpus
            size = num_gpus * batch_size + (num_gpus - 1)
            dataset = Subset(dataloader.dataset, range(size))
            dataloader = DataLoader(
                dataset,
                batch_size=self.hparams.batch_size,
                drop_last=False,
            )
            return dataloader

    hparams = tutils.get_default_hparams()
    hparams.batch_size = batch_size
    model = CurrentTestModel(hparams)

    trainer = Trainer(
        max_epochs=1,
        gpus=num_gpus,
    )

    # we expect the reduction for the metrics also to happen on the last batch
    # where we will get fewer metrics than gpus
    result = trainer.fit(model)
    assert 1 == result
