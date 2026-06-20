from pathlib import Path
from datetime import datetime, timedelta

from pytorch_lightning.utilities.types import EVAL_DATALOADERS
from torch.utils.data import DataLoader
from pytorch_lightning import LightningDataModule

from .batch_handling import HDF5CompetitionTablesDataset, random_crop_batch_to_smallest


class CompetitionDataModule(LightningDataModule):
    def __init__(
        self,
        data_dir: Path,
        batch_size: int,
        competition_table_period: timedelta,
        train_test_lim: datetime,
        hidden_part: float,
        num_workers: int,
    ):
        """
        Args:
            data_dir (pathlib.Path) : directory of the HDF5 files
            batch_size
            train_test_lim (datetime) : separation date between the train_val data and the test data
            hidden_part (float) : part of the data which is not given to the encoder and is used to evaluate the model
            num_workers (int) : number o workers used for the dataloader
        """
        super().__init__()
        self.batch_size = batch_size
        self.hidden_part = hidden_part
        self.num_workers = num_workers
        all_files = list(data_dir.glob("*.hdf5"))
        comp_dates = [datetime.fromisoformat(f.name[:10]) for f in all_files]
        self.train_val_files = [
            f for f, d in zip(all_files, comp_dates) if d <= train_test_lim
        ]
        self.test_files = [
            f
            for f, d in zip(all_files, comp_dates)
            if d > train_test_lim + competition_table_period
        ]

    def setup(self, stage):
        pass

    def train_dataloader(self):
        dataset = HDF5CompetitionTablesDataset(
            self.train_val_files, hidden_part=self.hidden_part
        )
        dataloader = DataLoader(
            dataset,
            batch_size=self.batch_size,
            shuffle=True,
            prefetch_factor=1,
            collate_fn=random_crop_batch_to_smallest,
            num_workers=self.num_workers,
        )
        return dataloader

    def test_dataloader(self):
        dataset = HDF5CompetitionTablesDataset(
            self.test_files, hidden_part=self.hidden_part
        )
        dataloader = DataLoader(
            dataset,
            batch_size=self.batch_size,
            collate_fn=random_crop_batch_to_smallest,
            num_workers=self.num_workers,
        )
        return dataloader
