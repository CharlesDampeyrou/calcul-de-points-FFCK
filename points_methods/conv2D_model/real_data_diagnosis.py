"""Diagnostic de gradient vanishing / exploding sur les données réelles (HDF5).

Reproduit la préparation de données du notebook ( ``CompetitionDataModule`` sur
``hdf5_data/1y_tables``) et entraîne le modèle sur quelques steps Adam avec le
calcul de loss exact de ``training_step``, tout en instrumentant le réseau
(hooks forward / backward) pour mesurer, couche par couche :

  - les normes d'activations (forward),
  - les normes de gradients entrants et sortants (backward),
  - les normes de gradients des paramètres et leur ratio sur les poids,
  - la présence éventuelle de NaN (division par un masque vide dans PELinear).

Usage (depuis la racine du dépôt) :

    python -m points_methods.conv2D_model.real_data_diagnosis \
        --steps 40 --configs 0,1 --callback

  --steps         nombre de steps Adam par configuration
  --configs       indices des configurations à tester (voir CONFIGS)
  --batch-size    taille de batch (le DataLoader recadre au plus petit)
  --callback      active aussi un mini-fit Lightning avec GradientMonitorCallback
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import torch

from .data_module import CompetitionDataModule
from .gradient_diagnostics import (
    CONFIG_SMALL,
    CONFIG_LARGE,
    _NetRecorder,
    _gradient_norms_by_layer,
)
from .net import CompetitionAutoencoderNet


CONFIGS = [
    ("reference (16, 3, z4)", CONFIG_SMALL),
    ("elargie (32, 4, z8)", dict(
        CONFIG_SMALL, hidden_channels_enc=32, hidden_channels_dec=32,
        nb_hidden_layers_enc=4, nb_hidden_layers_dec=4,
        zdim_line=8, zdim_col=8,
    )),
    ("large (64, 5, z8)", dict(
        CONFIG_SMALL, hidden_channels_enc=64, hidden_channels_dec=64,
        nb_hidden_layers_enc=5, nb_hidden_layers_dec=5,
        zdim_line=8, zdim_col=8,
    )),
]


def _one_loss(net, x, mask_v):
    """Calcul de loss identique à CompetitionAutoencoderNet.training_step."""
    x0_hat = net(x * mask_v.unsqueeze(1), mask_v)
    err = x0_hat - x[:, :1, :, :]
    err_visible = err * mask_v.unsqueeze(1)
    return net.loss_func(err_visible, torch.zeros_like(err_visible))


def diagnose_real(config, dataloader, steps, seed=0, verbose=True, name=""):
    torch.manual_seed(seed)
    net = CompetitionAutoencoderNet(**config)
    recorder = _NetRecorder(net)
    optimizer = torch.optim.Adam(net.parameters())

    it = iter(dataloader)

    def next_batch():
        nonlocal it
        try:
            return next(it)
        except StopIteration:
            it = iter(dataloader)
            return next(it)

    # --- Statistiques des masques sur les premiers batchs --------------------
    zero_row_v = zero_col_v = n_batches = 0
    for _ in range(3):
        x, mv, mh = next_batch()
        zero_row_v += (mv.sum(dim=2) == 0).float().sum().item()
        zero_col_v += (mv.sum(dim=1) == 0).float().sum().item()
        n_batches += x.shape[0]
    mask_report = dict(
        sample_size=n_batches,
        pct_lignes_masque_vide=100 * zero_row_v / n_batches,
        pct_colonnes_masque_vide=100 * zero_col_v / n_batches,
    )

    # --- Mesures à l'initialisation ------------------------------------------
    x, mv, mh = next_batch()
    net.zero_grad()
    loss0 = _one_loss(net, x, mv)
    loss0.backward()
    act_init = dict(recorder.act_norms)
    grads_init = _gradient_norms_by_layer(net)
    grad_out_init = dict(recorder.grad_out_norms)

    # --- Entraînement court sur les données réelles ---------------------------
    losses, grad_totals = [loss0.item()], []
    nan = False
    for _ in range(steps):
        x, mv, mh = next_batch()
        loss = _one_loss(net, x, mv)
        optimizer.zero_grad()
        loss.backward()
        layer_grads = _gradient_norms_by_layer(net)
        grad_totals.append(sum(g**2 for g, _ in layer_grads.values()) ** 0.5)
        optimizer.step()
        l = loss.item()
        losses.append(l)
        if l != l:  # NaN
            nan = True
            break

    # --- Probe final ----------------------------------------------------------
    net.eval()
    recorder.reset()
    x, mv, mh = next_batch()
    net.zero_grad()
    loss_final = _one_loss(net, x, mv)
    loss_final.backward()
    grads_final = _gradient_norms_by_layer(net)
    act_final = dict(recorder.act_norms)
    recorder.remove()

    # --- Verdicts --------------------------------------------------------------
    g0 = grad_totals[0]
    gN = grad_totals[-1]
    first10 = sum(grad_totals[:10]) / max(len(grad_totals[:10]), 1)
    last10 = sum(grad_totals[-10:]) / max(len(grad_totals[-10:]), 1)

    first_enc = sorted(
        (k for k in grads_final if k.startswith("encoder.layers")),
        key=lambda s: int(s.split(".")[2]),
    )[: max(1, config["nb_hidden_layers_enc"] // 3)]
    vanishing = any(
        grads_final[k][0] / max(grads_final[k][1], 1e-12) < 1e-7 for k in first_enc
    )
    exploding = (
        nan
        or gN > 1e3
        or (first10 > 0 and last10 / first10 > 100 and losses[-1] > losses[0])
    )

    result = dict(
        config=config, name=name, losses=losses, grad_totals=grad_totals, nan=nan,
        g0=g0, gN=gN, first10=first10, last10=last10,
        vanishing=vanishing, exploding=exploding, mask_report=mask_report,
        act_init=act_init, act_final=act_final,
        grads_init=grads_init, grads_final=grads_final,
        grad_out_init=grad_out_init,
    )
    if verbose:
        _print_report(result)
    return result


def _print_report(res):
    cfg = res["config"]
    print("=" * 78)
    print(f"{res['name']} — hidden={cfg['hidden_channels_enc']}, "
          f"layers={cfg['nb_hidden_layers_enc']}, zdim={cfg['zdim_line']}")
    print("=" * 78)
    m = res["mask_report"]
    print(f"Masques visibles sur {m['sample_size']} tables : "
          f"{m['pct_lignes_masque_vide']:.1f}% de lignes vides, "
          f"{m['pct_colonnes_masque_vide']:.1f}% de colonnes vides "
          f"(-> NaN dans PELinear si une ligne est vide)")
    print(f"loss : {res['losses'][0]:.4e} -> {res['losses'][-1]:.4e} "
          f"(NaN: {res['nan']})")
    print(f"||grad|| global : début {res['g0']:.4e}, fin {res['gN']:.4e} "
          f"(moy 10 premiers steps {res['first10']:.3e}, "
          f"10 derniers {res['last10']:.3e})")
    print()
    print("Activations à l'initialisation puis à la fin, par profondeur :")
    print(f"{'profondeur':>10} | {'||act|| init':>12} | {'||act|| fin':>12}")
    for i, (a0, a1) in enumerate(zip(res["act_init"].values(),
                                     res["act_final"].values())):
        print(f"{i:>10} | {a0:>12.4e} | {a1:>12.4e}")
    print()
    print("Gradients finaux par couche :")
    print(f"{'couche':<36} | {'||grad|| init':>12} | {'||grad|| fin':>12} "
          f"| {'ratio init':>10} | {'ratio fin':>10}")
    for k in sorted(res["grads_final"]):
        g0i, w0 = res["grads_init"].get(k, (float("nan"), 1.0))
        g1i, _ = res["grads_final"][k]
        print(f"{k:<36} | {g0i:>12.3e} | {g1i:>12.3e} "
              f"| {g0i / w0:>10.2e} | {g1i / w0:>10.2e}")
    print()
    verdicts = []
    if res["nan"]:
        verdicts.append("NaN dans la loss (masques vides dans PELinear ?)")
    if res["exploding"]:
        verdicts.append("EXPLODING (gradients énormes ou en croissance)")
    if res["vanishing"]:
        verdicts.append("VANISHING (gradients négligeables en tête d'encoder)")
    if not verdicts:
        verdicts.append("Aucun problème de gradient détecté sur ces steps.")
    print("VERDICT :")
    for v in verdicts:
        print(f"  - {v}")
    print()


def run_callback_probe(config, data_module, max_epochs=1, limit_train_batches=60):
    """Mini-fit Lightning avec le GradientMonitorCallback, sur données réelles."""
    from pytorch_lightning import Trainer, seed_everything
    from .gradient_diagnostics import GradientMonitorCallback

    seed_everything(0)
    net = CompetitionAutoencoderNet(**config)
    cb = GradientMonitorCallback()
    trainer = Trainer(
        callbacks=[cb],
        max_epochs=max_epochs,
        limit_train_batches=limit_train_batches,
        logger=False,
        enable_progress_bar=False,
        enable_checkpointing=False,
        num_sanity_val_steps=0,
    )
    trainer.fit(net, data_module.train_dataloader())
    print(cb.summary())
    metrics = {
        k: round(v.item(), 10)
        for k, v in trainer.callback_metrics.items()
        if k.startswith("grad_") and ("layers" in k or k == "grad_norm/total")
    }
    print("Dernières métriques loguées :")
    for k in sorted(metrics):
        print(f"  {k} = {metrics[k]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--configs", type=str, default="0,1")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--callback", action="store_true")
    parser.add_argument("--callback-only", action="store_true",
                        help="ne lance que le mini-fit Lightning (callback)")
    parser.add_argument("--limit-batches", type=int, default=60,
                        help="nb de batchs par epoch pour le mini-fit Lightning")
    args = parser.parse_args()

    files_saving_path = Path.cwd() / "hdf5_data" / "1y_tables"
    data_module = CompetitionDataModule(
        files_saving_path,
        batch_size=args.batch_size,
        competition_table_period=timedelta(days=365),
        train_test_lim=datetime(2023, 1, 1),
        hidden_part=0.15,
        num_workers=args.num_workers,
    )

    if not args.callback_only:
        results = []
        for i in [int(c) for c in args.configs.split(",")]:
            name, cfg = CONFIGS[i]
            res = diagnose_real(
                cfg, data_module.train_dataloader(), steps=args.steps, name=name
            )
            results.append(res)
        print("=" * 78)
        print("Comparaison finale :")
        for res in results:
            cfg = res["config"]
            print(
                f"  {res['name']:<24} loss {res['losses'][0]:.3e} -> "
                f"{res['losses'][-1]:.3e} (nan={res['nan']}), "
                f"||grad|| {res['g0']:.3e} -> {res['gN']:.3e}, "
                f"exploding={res['exploding']}, vanishing={res['vanishing']}"
            )

    if args.callback or args.callback_only:
        run_callback_probe(
            CONFIGS[0][1], data_module, limit_train_batches=args.limit_batches
        )


if __name__ == "__main__":
    main()
