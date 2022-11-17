from ...models.covnet import Net
from ...data.mnist_1989 import get_train_data, get_test_data
from ...trainers.classifier import train, test
import torch
from tensorboardX import SummaryWriter
import os
import sys

save_dir: str = os.environ.get("SAVE_DIR")
data_dir: str = os.environ.get("DATA_DIR")
network = Net()
optimizer = torch.optim.SGD(network.parameters(), lr=0.01, momentum=0.9)

writer = SummaryWriter(log_dir=save_dir)

command = sys.argv[1]

if command == "train":
    train(
        network,
        get_train_data(data_dir),
        get_test_data(data_dir),
        save_dir,
        optimizer=optimizer,
        writer=writer,
    )
elif command == "test":
    test(network, get_test_data(data_dir), save_dir, writer=writer)
