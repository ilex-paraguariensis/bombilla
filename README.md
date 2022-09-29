
# What is Bombilla?

Bombilla is a configuration format for describing python objects and executions in plain json. Bombilla is compatible with any python framework, e.g pytorch lightning, keras and jax. You can use bombilla to define an experiment with a json file, and then execute it. 

# Installation

bombilla can be installed with pip:

```bash
pip install bomba
```

# API

Example of using bombilla API:
```python
from bombilla import Bombilla

bombilla = Bombilla(bombilla_object_descriptor_dict)

# parses dict and loads modules, does not executes anything yet
bombilla.load()

# executes everything in the dictionary, creates objects
bombilla.execute()

# you can pass argument if you want to execute a function on a specific object (e.g. train a model)
bombilla.execute_method("trainer", "fit", *args, **kwargs)
 
# you can get the object by key
bombilla.find("resnet")
```


## Object descriptor format

An object descriptor is a dictionary that describes python objects and executions.
The dictionary can contain the following keys:
* `module`: the python module where the object is defined
* `class_name`: the name of the class
* `object_key`: the key of the object for dynamic referencing
* `params`: the parameters for creating the object
* `function`: the function to be executed
* `method_args`: arguments for calling a specific method on an object

**Note that all the arguments are directly passed to the object constructor, so you can use any argument that is accepted by the function's singnature.**


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


Or a simple jax execution configuration file that executes a function:

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