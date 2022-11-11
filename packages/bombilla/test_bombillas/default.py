from ...data.loaders.cifar10.data_loader import CifarLightningDataModule
from ...trainers.base_classification.base_classification import (
    LightningClassificationModule,
)
from ...models.resnet.resnet import ResNet
from ...models.resnet.resnet import BasicBlock
from torch.nn import BatchNorm2d
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau
from pytorch_lightning import Trainer
from pytorch_lightning.callbacks import EarlyStopping
from pytorch_lightning.callbacks import ModelCheckpoint
import os
from aim.pytorch_lightning import AimLogger

save_dir: str = os.environ.get("SAVE_DIR")
trainer = Trainer(
    gpus=1,
    max_epochs=100,
    precision=16,
    gradient_clip_val=0.5,
    enable_checkpointing=True,
    callbacks=[
        EarlyStopping(monitor="val_loss", patience=10, mode="min"),
        ModelCheckpoint(
            dirpath=f"{save_dir}/checkpoints",
            monitor="val_loss",
            save_top_k=1,
            verbose=True,
            save_last=True,
            mode="min",
        ),
    ],
    logger=AimLogger(
        experiment="default", train_metric_prefix="train_", val_metric_prefix="val_"
    ),
)
classifier = ResNet(
    block=BasicBlock,
    layers=[3, 4, 6, 3],
    num_classes=10,
    in_channels=3,
    zero_init_residual=False,
    groups=1,
    width_per_group=64,
    replace_stride_with_dilation=[False, False, False],
    norm_layer=BatchNorm2d,
)
optimizer = Adam(lr=0.0004, betas=[0.5, 0.999], params=classifier.parameters())
pl_model = LightningClassificationModule(
    classifier=classifier,
    optimizers={
        "optimizer": optimizer,
        "lr_scheduler": {
            "monitor": "val_loss",
            "scheduler": ReduceLROnPlateau(
                optimizer=optimizer,
                mode="min",
                factor=0.5,
                threshold=1e-08,
                threshold_mode="rel",
                patience=0,
                verbose=True,
            ),
        },
    },
)
data = CifarLightningDataModule(
    location="./data/cifar10", batch_size=32, image_size=[256, 256], crop_size=4
)
returns = {
    "train": [trainer.fit(model=pl_model, datamodule=data)],
    "test": [trainer.test(model=pl_model, datamodule=data)],
    "restart": [],
}
