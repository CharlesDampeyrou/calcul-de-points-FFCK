from typing import TYPE_CHECKING
import logging
from datetime import datetime
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from pytorch_lightning.trainer import Trainer
from pytorch_lightning.callbacks import ModelCheckpoint, TQDMProgressBar
from pytorch_lightning.core import LightningModule
from pytorch_lightning.loggers import TensorBoardLogger

if TYPE_CHECKING:
    from ...data_handling.conv_method_data_prep import ConvMethodDataPreparator
from .net import CompetitionAutoencoderNet
from .batch_handling import CompetitionTablesDataset, random_crop_batch_to_smallest


class CompetitionAutoencoderModel:
    def __init__(
        self,
        net_hyperparams: dict,
        data_preparator: "ConvMethodDataPreparator",
        saving_path: Path,
    ):
        self.logger = logging.getLogger("points_methods.conv2Dmodel")
        self.net_hyperparams = net_hyperparams
        self.saving_path = saving_path
        self.net = CompetitionAutoencoderNet(**net_hyperparams)
        self.data_preparator = data_preparator
        self.train_dataset = None
        self.val_dataset = None
        self.is_fitted = False
        if saving_path.exists():
            self.net = CompetitionAutoencoderNet.load_from_checkpoint(self.saving_path)
            self.logger.info("Neural network loaded.")
            self.is_fitted = True
        else:
            self.logger.warning("The neural network isn't trained for now.")

    def load_data(
        self,
        starting_date_train: datetime,
        ending_date_train: datetime,
        starting_date_val: datetime,
        ending_date_val: datetime,
    ):
        train_scores, train_categories, train_mask = (
            self.data_preparator.get_competition_tensors_over_period(
                starting_date=starting_date_train, ending_date=ending_date_train
            )
        )
        val_scores, val_categories, val_mask = (
            self.data_preparator.get_competition_tensors_over_period(
                starting_date=starting_date_val, ending_date=ending_date_val
            )
        )
        self.train_dataset = CompetitionTablesDataset(
            train_scores, train_categories, train_mask
        )
        self.val_dataset = CompetitionTablesDataset(
            val_scores, val_categories, val_mask
        )

    def train(
        self,
        starting_date_train: datetime,
        ending_date_train: datetime,
        starting_date_val: datetime,
        ending_date_val: datetime,
        batch_size: int = 16,
        num_workers: int = 4,
        max_epochs: int = 10,
    ) -> None:
        train_scores, train_categories, train_mask = (
            self.data_preparator.get_competition_tensors_over_period(
                starting_date=starting_date_train, ending_date=ending_date_train
            )
        )
        val_scores, val_categories, val_mask = (
            self.data_preparator.get_competition_tensors_over_period(
                starting_date=starting_date_val, ending_date=ending_date_val
            )
        )
        train_dataset = CompetitionTablesDataset(
            train_scores, train_categories, train_mask
        )
        val_dataset = CompetitionTablesDataset(val_scores, val_categories, val_mask)
        train_dataloader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            collate_fn=random_crop_batch_to_smallest,
            num_workers=num_workers,
        )
        val_dataloader = DataLoader(
            val_dataset,
            batch_size=batch_size,
            collate_fn=random_crop_batch_to_smallest,
            num_workers=num_workers,
        )
        checkpoint_callback = ModelCheckpoint(
            monitor="validation loss",
            mode="min",
            save_top_k=1,
            dirpath=self.saving_path.parent,
            filename=self.saving_path.name,
        )
        tqdm_bar = TQDMProgressBar(refresh_rate=1)
        logger = TensorBoardLogger(
            save_dir=Path.cwd() / "lightning_logs", name="self.saving_path.name"
        )
        trainer = Trainer(
            callbacks=[checkpoint_callback, tqdm_bar],
            max_epochs=max_epochs,
            log_every_n_steps=1,
            logger=logger,
        )
        trainer.fit(
            self.net,
            train_dataloader,
            val_dataloader,
        )

    def predict(self, data, mask): ...
