from typing import List, Tuple
from pathlib import Path

import h5py
import torch


class HDF5CompetitionTablesDataset(torch.utils.data.Dataset):
    """Class to get the data used for the convolution model"""

    def __init__(self, files_list: List[Path], hidden_part: float):
        """
        Args:
            files_list (List[pathlib.Path]) : list of paths to the HDF5 files
            hidden_part (float, between 0 and 1) : the part of the data not given to the model to the model's encoder and only used to evaluate the model
        """
        self.hidden_part = hidden_part
        self.files_list = files_list

    def __len__(self):
        return len(self.files_list)

    def __getitem__(
        self, idx: int
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        with h5py.File(self.files_list[idx], "r") as f:
            scores = torch.from_numpy(f["scores"][:])  # type: ignore
            categories = torch.from_numpy(f["categories"][:])  # type: ignore
            mask = torch.from_numpy(f["mask"][:])  # type: ignore
            hash_t = torch.from_numpy(f["hash"][:])  # type: ignore
        normalized_hash = hash_t % 10**6 / 10**6
        hash_comp = normalized_hash < self.hidden_part
        mask_visible = mask & (~hash_comp)
        mask_hidden = mask & (hash_comp)
        kept_cols = mask_visible.sum(dim=0) > 0
        return (
            scores[:, kept_cols],
            categories[kept_cols, :],
            mask_visible[:, kept_cols],
            mask_hidden[:, kept_cols],
        )


def random_crop_batch_to_smallest(
    raw_batch: List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]],
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Transforms a list of samples of different sizes into a batch.

    Args:
        raw_batch : tuple containing
            scores_l (List[torch.f32tensor]) : the tensors have a shape (nb_competitions, nb_competitors) where the two paramters may change over the list.
            categories_l : list of bool tensors of shape (nb_competitors, 5)
            mask_visible_l : list of bool tensors of shape (nb_competitions, nb_compeitors)
            mask_hidden_l : list of bool tensors of shape (nb_competitions, nb_compeitors)

    Returns:
        data : f32 torch.tensor of shape (len(scores), 6, min_nb_competitions, min_nb_competitors)
        visible_masks : f32 torch.tensor of shape (len(scores), min_nb_competitions, min_nb_competitors)
        hidden_masks : f32 torch.tensor of shape (len(scores), min_nb_competitions, min_nb_competitors)

    min_nb_competitions and min_nb_competitors are respectively the minimum numbers of lines and of columns of the scores tensors. Tensors of scores with more lines or columns have random selected lines or columns removed. The same colomns are removed from categories and masks, and the same lines from masks. The categories are repeted over each line and are concatenated with the scores. All the tensors are then stacked.
    """
    scores, categories, masks_visible, masks_hidden = zip(*raw_batch)
    min_rows = min(t.shape[0] for t in scores)
    cropped_rows_data = []
    cropped_rows_v_masks = []
    cropped_rows_h_masks = []
    for s, c, mv, mh in raw_batch:
        nb_rows, nb_cols = s.shape[0], s.shape[1]
        # indices aléatoires pour les lignes à conserver
        rows = torch.randperm(nb_rows)[:min_rows]
        s = s.index_select(0, rows)
        mv = mv.index_select(0, rows)
        mh = mh.index_select(0, rows)
        # si des competiteurs n'ont pas de competition visible, on les enlève
        no_comp_cols = mv.sum(dim=0) == 0
        s = s[:, ~no_comp_cols]
        c = c[~no_comp_cols, :]
        mv = mv[:, ~no_comp_cols]
        mh = mh[:, ~no_comp_cols]

        cropped_rows_data.append(
            torch.cat(
                [
                    s.unsqueeze(0),  # scores mis en forme
                    c.unsqueeze(0).expand(s.shape[0], -1, -1).permute(2, 0, 1),
                ]
            )
        )
        cropped_rows_v_masks.append(mv)
        cropped_rows_h_masks.append(mh)
    min_cols = min(m.shape[1] for m in cropped_rows_v_masks)
    cropped_data = []
    cropped_v_masks = []
    cropped_h_masks = []
    for d, mv, mh in zip(cropped_rows_data, cropped_rows_v_masks, cropped_rows_h_masks):
        nb_cols = mv.shape[1]
        cols = torch.randperm(nb_cols)[:min_cols]
        cropped_data.append(d.index_select(2, cols))
        cropped_v_masks.append(mv.index_select(1, cols))
        cropped_h_masks.append(mh.index_select(1, cols))

    data = torch.stack(cropped_data)
    visible_masks = torch.stack(cropped_v_masks)
    hidden_masks = torch.stack(cropped_h_masks)
    return data, visible_masks, hidden_masks
