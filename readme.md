
# What is Bambilla?

Bambilla is a python library for experimental and reproducible research. Bambilla is a python object descriptor in plain json and can be used to execute a configuration. Bambilla is compatible with any python framework for example pytorch lightning, keras and jax. If you need to experiment with hyperparameters and keep track of your experiments, bambilla is for you. Bambilla in a nutshell: define your experiment and hyperparameters in a json configuration file and then execute it with bambilla. 

# Installation

Bambilla is available on pypi. You can install it with pip:
```
pip install bambilla
```

# Usage

To use bambilla, you need to define your experiment in a json configuration file. The configuration file is a dictionary with objects described in plain json. Bambilla can be called to execute everything in the configuration file. 

For example, here an object is described from `torchvision.models` python module, and used to load a pre-trained resnet.

```
"resnet":{
   "module":"torchvision.models",
   "class_name":"resnet18",
   "object_key":"resnet",
   "params":{
      "pretrained":true
   }
}

```


You can use bambilla minimally, for example, a simple jax execution configuration file is:

```
{
    "data": {
        "module": "data_loader.datasets",
        "function": "mnist",
        "object_key": "data",
        "params": {
            "permute_train": true
        }
    },
    "train_function": {
        "module": "trainers.mnist_classifier",
        "function": "train",
        "params": {
            "datasets": "{data}",
            "step_size": 0.001,
            "num_epochs": 10,
            "batch_size": 128,
            "momentum_mass": 0.9
        }
    }
}
```

Or you can call methods on objects:
```
{
    "data": {
        "module": "data_loaders.cifar10.data_loader",
        "function": "get_train_data_loader",
        "object_key": "data",
        "params": {
            "batch_size": 128
        }
    },
    "trainer": {
        "module": "modules.resnet.resnet",
        "function": "get_model",
        "params": {
            "input_shape": [
                180,
                180,
                3
            ],
            "num_classes": 2
        },
        "object_key": "model",
        "method_args": [
            {
                "function": "compile",
                "params": {
                    "optimizer": {
                        "module": "tensorflow.keras.optimizers",
                        "class_name": "Adam",
                        "params": {
                            "learning_rate": 0.001
                        }
                    },
                    "loss": "binary_crossentropy",
                    "metrics": [
                        "accuracy"
                    ]
                }
            },
            {
                "function": "fit",
                "params": {
                    "": "{data}",
                    "epochs": 10
                }
            }
        ]
    }
}
```



And describe a nested dictionary of any depth:
```
{
    "data": {
        "module": "data_loaders.cifar10.data_loader",
        "class_name": "CifarLightningDataModule",
        "object_key": "data",
        "params": {
            "location": "./data/cifar10",
            "batch_size": 128,
            "image_size": [
                256,
                256
            ],
            "crop_size": 4
        }
    },
    "pytorch_lightning_module": {
        "module": "base_classification",
        "class_name": "LightningClassificationModule",
        "object_key": "pl_model",
        "params": {
            "classifier": {
                "module": "modules.resnet.resnet",
                "object_key": "classifier",
                "class_name": "ResNet",
                "params": {
                    "block": "BasicBlock",
                    "layers": [
                        3,
                        4,
                        6,
                        3
                    ],
                    "num_classes": 10,
                    "in_channels": 3,
                    "zero_init_residual": false,
                    "groups": 1,
                    "width_per_group": 64,
                    "replace_stride_with_dilation": [
                        false,
                        false,
                        false
                    ],
                    "norm_layer": "BatchNorm2d"
                }
            },
            "optimizers": {
                "optimizer": {
                    "module": "torch.optim",
                    "class_name": "Adam",
                    "object_key": "optimizer",
                    "params": {
                        "lr": 0.0004,
                        "betas": [
                            0.5,
                            0.999
                        ],
                        "params": {
                            "function_call": "parameters",
                            "reference_key": "classifier",
                            "params": {}
                        }
                    }
                },
                "lr_scheduler": {
                    "monitor": "val_loss",
                    "scheduler": {
                        "module": "torch.optim.lr_scheduler",
                        "class_name": "ReduceLROnPlateau",
                        "params": {
                            "optimizer": "{optimizer}",
                            "mode": "min",
                            "factor": 0.5,
                            "threshold": 1e-08,
                            "threshold_mode": "rel",
                            "patience": 0,
                            "verbose": true
                        }
                    }
                }
            }
        }
    },
    "trainer": {
        "module": "pytorch_lightning",
        "class_name": "Trainer",
        "params": {
            "gpus": 1,
            "max_epochs": 100,
            "precision": 16,
            "gradient_clip_val": 0.5,
            "enable_checkpointing": true,
            "callbacks": [
                {
                    "module": "pytorch_lightning.callbacks",
                    "class_name": "EarlyStopping",
                    "params": {
                        "monitor": "val_loss",
                        "patience": 10,
                        "mode": "min"
                    }
                },
                {
                    "module": "pytorch_lightning.callbacks",
                    "class_name": "ModelCheckpoint",
                    "params": {
                        "dirpath": "{save_dir}/checkpoints",
                        "monitor": "val_loss",
                        "save_top_k": 1,
                        "verbose": true,
                        "save_last": true,
                        "mode": "min"
                    }
                }
            ],
            "logger": {
                "module": "pytorch_lightning.loggers",
                "class_name": "CSVLogger",
                "params": {
                    "save_dir": "./logs"
                }
            }
        },
        "method_args": [
            {
                "function": "fit",
                "params": {
                    "model": "{pl_model}",
                    "datamodule": "{data}"
                }
            },
            {
                "function": "test",
                "params": {
                    "model": "{pl_model}",
                    "datamodule": "{data}"
                }
            }
        ]
    }
}
```