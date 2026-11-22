"""Diagnostic de gradient vanishing / exploding pour CompetitionAutoencoderNet.

Deux outils :

1. ``GradientMonitorCallback`` : callback Lightning à brancher dans le Trainer.
   À chaque step d'optimisation, il logue la norme L2 du gradient et le ratio
   ``||grad|| / ||poids||`` (invariant d'échelle) par couche, ainsi que des
   compteurs d'alertes vanishing/exploding consultables via ``.summary()``.

2. ``diagnose()`` : exécution autonome (données synthétiques) qui instrumente
   le réseau avec des hooks forward/backward et compare le comportement de la
   petite et de la grande configuration, à l'initialisation puis sur quelques
   steps Adam.

Usage :

    python -m points_methods.conv2D_model.gradient_diagnostics
"""

from collections import defaultdict

import torch
import pytorch_lightning as pl

from .blocks import PELinear


# --------------------------------------------------------------------------- #
# 1. Callback Lightning pour l'entraînement réel
# --------------------------------------------------------------------------- #


class GradientMonitorCallback(pl.Callback):
    """Logue les normes de gradients par couche et détecte vanishing/exploding.

    Seuils (sur des données de l'ordre de l'unité, ce qui est le cas ici
    puisque les erreurs sont en minutes de scores) :
      - vanishing : ratio ||grad|| / ||poids|| < ``vanishing_ratio``
      - exploding : ||grad|| > ``exploding_grad`` ou ratio > ``exploding_ratio``

    Les scalaires sont loggués sous ``grad_norm/<couche>`` et
    ``grad_ratio/<couche>`` (visibles dans TensorBoard).
    """

    def __init__(
        self,
        vanishing_ratio=1e-7,
        exploding_grad=1e3,
        exploding_ratio=10.0,
        alert_every_n_steps=50,
        verbose=True,
    ):
        super().__init__()
        self.vanishing_ratio = vanishing_ratio
        self.exploding_grad = exploding_grad
        self.exploding_ratio = exploding_ratio
        self.alert_every_n_steps = alert_every_n_steps
        self.verbose = verbose
        self.violations = defaultdict(int)  # type de violation -> nb de steps
        self.history = []  # [(global_batch_idx, {couche: (grad_norm, ratio)})]

    def on_before_optimizer_step(self, trainer, pl_module, optimizer):
        # Somme des carrés par groupe logique de couche
        groups = defaultdict(lambda: [0.0, 0.0])
        total_sq = 0.0
        for name, p in pl_module.named_parameters():
            if p.grad is None:
                continue
            gn_sq = p.grad.norm().item() ** 2
            total_sq += gn_sq
            # "encoder.layers.0.direct_conv.weight" -> "encoder.layers.0"
            key = ".".join(name.split(".")[:3]) if name.count(".") >= 3 else name
            groups[key][0] += gn_sq
            groups[key][1] += p.norm().item() ** 2

        total_norm = total_sq**0.5
        pl_module.log("grad_norm/total", total_norm)
        snapshot = {}
        for key, (g_sq, w_sq) in sorted(groups.items()):
            g = g_sq**0.5
            w = max(w_sq**0.5, 1e-12)
            ratio = g / w
            pl_module.log(f"grad_norm/{key}", g)
            pl_module.log(f"grad_ratio/{key}", ratio)
            snapshot[key] = (g, ratio)

        idx = trainer.global_step
        self.history.append((idx, total_norm, snapshot))

        # Détection des violations
        step_violations = []
        if total_norm > self.exploding_grad:
            step_violations.append(f"exploding (total grad norm {total_norm:.3e})")
        if not torch.isfinite(torch.tensor(total_norm)):
            step_violations.append("gradients non finis (NaN/Inf)")
        for key, (g, ratio) in snapshot.items():
            if ratio < self.vanishing_ratio:
                step_violations.append(f"vanishing ({key}: ratio {ratio:.3e})")
            elif ratio > self.exploding_ratio or g > self.exploding_grad:
                step_violations.append(
                    f"exploding ({key}: grad {g:.3e}, ratio {ratio:.3e})"
                )
        for v in step_violations:
            # clé sans les nombres, pour compter par famille de violation
            family = v.split(" (")[0]
            self.violations[family] += 1
        if self.verbose and step_violations and idx % self.alert_every_n_steps == 0:
            print(f"[GradientMonitor] step {idx} : {sorted(set(step_violations))}")

    def summary(self):
        lines = ["--- Résumé GradientMonitorCallback ---"]
        if not self.violations:
            lines.append("Aucune violation détectée.")
        for family, count in sorted(self.violations.items()):
            lines.append(f"{family}: {count} steps concernés")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 2. Diagnostic autonome sur données synthétiques
# --------------------------------------------------------------------------- #

# Configuration "de référence" (celle du notebook / entraînements existants)
CONFIG_SMALL = dict(
    in_channels_enc=6,
    hidden_channels_enc=16,
    nb_hidden_layers_enc=3,
    zdim_line=4,
    zdim_col=4,
    hidden_channels_dec=16,
    nb_hidden_layers_dec=3,
    huber_loss_delta=5 / 90,
)

# Configuration "élargie" : à ajuster selon les dimensions qui posent problème
CONFIG_LARGE = dict(
    in_channels_enc=6,
    hidden_channels_enc=128,
    nb_hidden_layers_enc=7,
    zdim_line=16,
    zdim_col=16,
    hidden_channels_dec=128,
    nb_hidden_layers_dec=7,
    huber_loss_delta=5 / 90,
)


class _NetRecorder:
    """Collecte, via des hooks, les normes d'activations et de gradients."""

    def __init__(self, net):
        self.act_norms = {}  # nom de module PELinear -> norme de la sortie
        self.grad_in_norms = {}
        self.grad_out_norms = {}
        self.handles = []
        for name, mod in net.named_modules():
            if isinstance(mod, PELinear):
                self.handles.append(
                    mod.register_forward_hook(self._make_fwd_hook(name))
                )
                self.handles.append(
                    mod.register_full_backward_hook(self._make_bwd_hook(name))
                )

    def _make_fwd_hook(self, name):
        def hook(module, inputs, output):
            self.act_norms[name] = output.norm().item()
        return hook

    def _make_bwd_hook(self, name):
        def hook(module, grad_input, grad_output):
            if grad_output[0] is not None:
                self.grad_out_norms[name] = grad_output[0].norm().item()
            if grad_input[0] is not None:
                self.grad_in_norms[name] = grad_input[0].norm().item()
        return hook

    def reset(self):
        self.act_norms.clear()
        self.grad_in_norms.clear()
        self.grad_out_norms.clear()

    def remove(self):
        for h in self.handles:
            h.remove()


def _gradient_norms_by_layer(net):
    """Norme L2 des gradients, agrégée par couche logique."""
    groups = defaultdict(lambda: [0.0, 0.0])
    for name, p in net.named_parameters():
        if p.grad is None:
            continue
        key = ".".join(name.split(".")[:3]) if name.count(".") >= 3 else name
        groups[key][0] += p.grad.norm().item() ** 2
        groups[key][1] += p.norm().item() ** 2
    return {
        k: (g_sq**0.5, max(w_sq**0.5, 1e-12)) for k, (g_sq, w_sq) in groups.items()
    }


def _make_batch(batch_size, in_channels, h, w, seed):
    g = torch.Generator().manual_seed(seed)
    x = torch.randn(batch_size, in_channels, h, w, generator=g)
    # les masques réels sont 2D : (batch, lignes, colonnes)
    mask_v = (torch.rand(batch_size, h, w, generator=g) < 0.7).float()
    mask_h = (torch.rand(batch_size, h, w, generator=g) < 0.3).float()
    return x, mask_v, mask_h


def diagnose(config, steps=50, batch_size=4, h=24, w=16, seed=0, verbose=True):
    """Fait ''steps`` pas d'Adam sur données synthétiques et diagnostique.

    Retourne un dict avec les mesures clés : normes de gradients et
    d'activations à l'initialisation, évolution sur les steps, verdicts.
    """
    from .net import CompetitionAutoencoderNet

    torch.manual_seed(seed)
    net = CompetitionAutoencoderNet(**config)
    recorder = _NetRecorder(net)
    optimizer = torch.optim.Adam(net.parameters())

    x, mask_v, mask_h = _make_batch(batch_size, config["in_channels_enc"], h, w, seed)

    # --- Mesures à l'initialisation (avant tout step d'optimisation) ---------
    net.zero_grad()
    x0_hat = net(x * mask_v.unsqueeze(1), mask_v)
    err_visible = (x0_hat - x[:, :1, :, :]) * mask_v.unsqueeze(1)
    loss0 = net.loss_func(err_visible, torch.zeros_like(err_visible))
    loss0.backward()
    grads_init = _gradient_norms_by_layer(net)
    act_init = dict(recorder.act_norms)
    grad_in_init = dict(recorder.grad_in_norms)
    grad_out_init = dict(recorder.grad_out_norms)

    # --- Entraînement court ---------------------------------------------------
    losses = [loss0.item()]
    grad_totals = []
    grad_snapshots = []  # (grads par couche au fil des steps)
    for step in range(steps):
        net.train()
        x0_hat = net(x * mask_v.unsqueeze(1), mask_v)
        err_visible = (x0_hat - x[:, :1, :, :]) * mask_v.unsqueeze(1)
        loss = net.loss_func(err_visible, torch.zeros_like(err_visible))
        optimizer.zero_grad()
        loss.backward()
        layer_grads = _gradient_norms_by_layer(net)
        total = sum(g**2 for g, _ in layer_grads.values()) ** 0.5
        grad_totals.append(total)
        grad_snapshots.append(layer_grads)
        optimizer.step()
        losses.append(loss.item())

    # --- Dernière passe en mode évaluation/profiling --------------------------
    net.eval()
    recorder.reset()
    x0_hat = net(x * mask_v.unsqueeze(1), mask_v)
    err_visible = (x0_hat - x[:, :1, :, :]) * mask_v.unsqueeze(1)
    loss_final = net.loss_func(err_visible, torch.zeros_like(err_visible))
    net.zero_grad()
    loss_final.backward()
    grads_final = _gradient_norms_by_layer(net)
    act_final = dict(recorder.act_norms)
    grad_in_final = dict(recorder.grad_in_norms)
    grad_out_final = dict(recorder.grad_out_norms)
    recorder.remove()

    # --- Verdicts --------------------------------------------------------------
    finite = all(torch.isfinite(torch.tensor(v)).item() for v in
                 list(grad_totals) + list(losses))
    # exploding : gradients énormes, non finis, ou qui croissent au fil du temps
    g0, gN = grad_totals[0], grad_totals[-1]
    exploding_training = (
        (not finite) or gN > 1e3 or (g0 > 0 and gN / g0 > 100 and losses[-1] > losses[0])
    )
    # vanishing : les premières couches de l'encoder ne reçoivent presque plus
    # de gradient à la fin de l'entraînement
    first_enc_layer = sorted(
        (k for k in grads_final if k.startswith("encoder.layers")),
        key=lambda s: int(s.split(".")[2]),
    )
    vanishing = any(
        grads_final[k][0] / max(grads_final[k][1], 1e-12) < 1e-7 for k in first_enc_layer
    )
    # exploding à l'init : les normes d'activations ou de gradients de sortie
    # doublent systématiquement de couche en couche
    def layer_sequences(stats):
        """Séquences (encoder.hidden..., decoder.net...) dans l'ordre de profondeur."""
        seqs = defaultdict(list)
        for k in stats:
            parts = k.split(".")
            if parts[1] in ("layers", "net"):
                seqs[parts[0]].append((int(parts[2]), stats[k], k))
        return {
            block: [v for _, v, _ in sorted(items)] for block, items in seqs.items()
        }

    def depth_growth(stats, predicate):
        """Nombre max de transitions successives couche -> couche où predicate(a, b)
        est vrai, mesuré séparément dans l'encoder et le decoder.
        Retourne aussi les valeurs aplaties dans l'ordre de profondeur."""
        streak = best = 0
        flat = []
        for block_vals in layer_sequences(stats).values():
            flat.extend(block_vals)
            for a, b in zip(block_vals, block_vals[1:]):
                if a > 0 and predicate(a, b):
                    streak += 1
                    best = max(best, streak)
                else:
                    streak = 0
        return best, flat

    act_growth, act_vals = depth_growth(act_init, lambda a, b: b > 2 * a)
    grad_growth, grad_vals = depth_growth(grad_out_init, lambda a, b: b > 2 * a)
    exploding_init = act_growth >= 2 or grad_growth >= 2 or g0 > 1e3

    result = dict(
        config=config,
        finite=finite,
        loss_first=losses[0],
        loss_last=losses[-1],
        grad_total_first=g0,
        grad_total_last=gN,
        exploding_training=exploding_training,
        vanishing=vanishing,
        exploding_init=exploding_init,
        act_norms_init=act_vals,
        grad_out_norms_init=grad_vals,
        grads_init=grads_init,
        grads_final=grads_final,
        grad_totals=grad_totals,
        losses=losses,
    )

    if verbose:
        _print_report(result)
    return result


def _print_report(res):
    cfg = res["config"]
    print("=" * 78)
    print(f"Diagnostic — hidden={cfg['hidden_channels_enc']}, "
          f"layers={cfg['nb_hidden_layers_enc']}, zdim={cfg['zdim_line']}")
    print("=" * 78)
    print(f"loss   : {res['loss_first']:.4e} -> {res['loss_last']:.4e}")
    print(f"||grad|| global : {res['grad_total_first']:.4e} -> "
          f"{res['grad_total_last']:.4e}")
    print(f"fini (aucun NaN/Inf) : {res['finite']}")
    print()
    print("Normes à l'initialisation, en suivant la profondeur "
          "(activations en forward, grad sortant en backward) :")
    print(f"{'profondeur':>10} | {'||activation||':>14} | {'||grad out||':>12}")
    for i, (a, g) in enumerate(zip(res["act_norms_init"], res["grad_out_norms_init"])):
        print(f"{i:>10} | {a:>14.4e} | {g:>12.4e}")
    print()
    print("Gradients finaux par couche (norme du gradient, ratio sur les poids) :")
    print(f"{'couche':<32} | {'||grad||':>10} | {'||grad||/||w||':>14}")
    for k, (g, w) in sorted(res["grads_final"].items()):
        print(f"{k:<32} | {g:>10.3e} | {g / w:>14.3e}")
    print()
    verdicts = []
    if not res["finite"]:
        verdicts.append("GRADIENT EXPLODING en entraînement (NaN/Inf, loss diverge)")
    if res["exploding_init"]:
        verdicts.append(
            "EXPLODING à l'initialisation (activations ou gradients multipliés "
            "par >=2 de façon répétée en profondeur)"
        )
    if res["exploding_training"]:
        verdicts.append("EXPLODING en entraînement (norme de gradient croissante)")
    if res["vanishing"]:
        verdicts.append("VANISHING (gradients négligeables dans les premières couches)")
    if not verdicts:
        verdicts.append("Aucun problème de gradient détecté avec ces dimensions.")
    print("VERDICT :")
    for v in verdicts:
        print(f"  - {v}")
    print()


def run_all_diagnostics(steps=50, verbose=True):
    """Compare la config de référence, une config élargie et une très élargie."""
    configs = [
        CONFIG_SMALL.copy(),
        CONFIG_LARGE.copy(),
        dict(
            CONFIG_LARGE,
            hidden_channels_enc=512,
            hidden_channels_dec=512,
            nb_hidden_layers_enc=12,
            nb_hidden_layers_dec=12,
            zdim_line=64,
            zdim_col=64,
        ),
    ]
    results = []
    for cfg in configs:
        results.append(diagnose(cfg, steps=steps, verbose=verbose))
    if verbose:
        print("=" * 78)
        print("Comparaison finale (norme globale du gradient, dernière step) :")
        for res in results:
            cfg = res["config"]
            print(
                f"  hidden={cfg['hidden_channels_enc']:>4}, "
                f"layers={cfg['nb_hidden_layers_enc']:>2}, "
                f"zdim={cfg['zdim_line']:>2} : "
                f"loss {res['loss_first']:.3e} -> {res['loss_last']:.3e}, "
                f"||grad|| {res['grad_total_first']:.3e} -> "
                f"{res['grad_total_last']:.3e}, "
                f"exploding_init={res['exploding_init']}, "
                f"exploding_train={res['exploding_training']}, "
                f"vanishing={res['vanishing']}"
            )
    return results


if __name__ == "__main__":
    run_all_diagnostics()
