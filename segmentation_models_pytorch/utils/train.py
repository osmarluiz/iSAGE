import sys
import torch
from tqdm import tqdm as tqdm
from .meter import AverageValueMeter


class Epoch:
    def __init__(self, model, loss, metrics, stage_name, device="cpu", verbose=True, batch_callback=None):
        self.model = model
        self.loss = loss
        self.metrics = metrics
        self.stage_name = stage_name
        self.verbose = verbose
        self.device = device
        self.batch_callback = batch_callback

        self._to_device()

    def _to_device(self):
        self.model.to(self.device)
        self.loss.to(self.device)
        for metric in self.metrics:
            metric.to(self.device)

    def _format_logs(self, logs):
        str_logs = ["{} - {:.4}".format(k, v) for k, v in logs.items()]
        s = ", ".join(str_logs)
        return s

    def batch_update(self, x, y, batch_count=0):
        raise NotImplementedError

    def on_epoch_start(self):
        pass

    def run(self, dataloader):
        self.on_epoch_start()

        logs = {}
        loss_meter = AverageValueMeter()
        metrics_meters = {
            metric.__name__: AverageValueMeter() for metric in self.metrics
        }

        with tqdm(
            dataloader,
            desc=self.stage_name,
            file=sys.stdout,
            disable=not (self.verbose),
        ) as iterator:
            batch_count = 0
            total_batches = len(dataloader)
            for x, y in iterator:
                batch_count += 1
                x, y = x.to(self.device), y.to(self.device)
                loss, y_pred = self.batch_update(x, y, batch_count)

                # update loss logs
                loss_value = loss.cpu().detach().numpy()
                loss_meter.add(loss_value)
                loss_name = getattr(self.loss, '__name__', self.loss.__class__.__name__)
                loss_logs = {loss_name: loss_meter.mean}
                logs.update(loss_logs)

                # update metrics logs
                for metric_fn in self.metrics:
                    metric_value = metric_fn(y_pred, y).cpu().detach().numpy()
                    metrics_meters[metric_fn.__name__].add(metric_value)
                metrics_logs = {k: v.mean for k, v in metrics_meters.items()}
                logs.update(metrics_logs)

                if self.verbose:
                    s = self._format_logs(logs)
                    iterator.set_postfix_str(s)

                # Call batch callback if provided (for real-time monitoring)
                if self.batch_callback:
                    try:
                        self.batch_callback(
                            batch_idx=batch_count - 1,
                            total_batches=total_batches,
                            current_loss=float(loss_value),
                            phase=self.stage_name
                        )
                    except Exception as e:
                        # Don't let callback errors break training
                        pass

        return logs


class TrainEpoch(Epoch):
    def __init__(self, model, loss, metrics, optimizer, device="cpu", verbose=True, batch_callback=None, use_amp=False, scaler=None):
        super().__init__(
            model=model,
            loss=loss,
            metrics=metrics,
            stage_name="train",
            device=device,
            verbose=verbose,
            batch_callback=batch_callback,
        )
        self.optimizer = optimizer
        self.use_amp = use_amp
        self.scaler = scaler if scaler is not None else torch.amp.GradScaler('cuda', enabled=use_amp)

    def on_epoch_start(self):
        self.model.train()

    def batch_update(self, x, y, batch_count=0):
        self.optimizer.zero_grad()

        # Mixed precision forward pass
        with torch.amp.autocast('cuda', enabled=self.use_amp):
            prediction = self.model.forward(x)
            loss = self.loss(prediction, y)

        # Mixed precision backward pass
        if self.use_amp:
            self.scaler.scale(loss).backward()
            self.scaler.step(self.optimizer)
            self.scaler.update()
        else:
            loss.backward()
            self.optimizer.step()

        return loss, prediction


class ValidEpoch(Epoch):
    def __init__(self, model, loss, metrics, device="cpu", verbose=True, batch_callback=None, use_amp=False):
        super().__init__(
            model=model,
            loss=loss,
            metrics=metrics,
            stage_name="valid",
            device=device,
            verbose=verbose,
            batch_callback=batch_callback,
        )
        self.use_amp = use_amp

    def on_epoch_start(self):
        self.model.eval()

    def batch_update(self, x, y, batch_count=0):
        with torch.no_grad():
            # Mixed precision forward pass (validation)
            with torch.amp.autocast('cuda', enabled=self.use_amp):
                prediction = self.model.forward(x)
                loss = self.loss(prediction, y)

        return loss, prediction
