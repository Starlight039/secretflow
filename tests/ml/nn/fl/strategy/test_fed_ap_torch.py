import torch
import torch.optim as optim
from torch.nn import CrossEntropyLoss
from torch.utils.data import DataLoader, TensorDataset
from torchmetrics import Accuracy, Precision, Recall
from secretflow.ml.nn.fl.backend.torch.strategy.fed_ap import FedAP
from tests.ml.nn.fl.model_def import ConvNet

class TestFedAP:
    def test_fed_ap_local_step(self, sf_simulation_setup_devices):

        class ConvNetBuilder:
            def __init__(self):
                self.metrics = [
                    lambda: Accuracy(task="multiclass", num_classes=10, average='macro')
                ]

            def model_fn(self):
                return ConvNet()

            def loss_fn(self):
                return CrossEntropyLoss()

            def optim_fn(self, parameters):
                return optim.Adam(parameters)

        # Initialize FedAP strategy with ConvNet model
        conv_net_builder = ConvNetBuilder()
        fed_ap_worker = FedAP(builder_base=conv_net_builder)

        # Prepare dataset
        x_test = torch.rand(128, 1, 28, 28)  # Randomly generated data
        y_test = torch.randint(0, 10, (128,))  # Randomly generated labels for a 10-class task
        test_loader = DataLoader(TensorDataset(x_test, y_test), batch_size=32, shuffle=True)
        fed_ap_worker.train_set = iter(test_loader)
        fed_ap_worker.train_iter = iter(fed_ap_worker.train_set)

        # Perform a training step
        gradients = None
        gradients, num_sample = fed_ap_worker.train_step(
            gradients, cur_steps=0, train_steps=1
        )

        # Apply weights update
        fed_ap_worker.apply_weights(gradients)

        # Assert the sample number and length of gradients
        assert num_sample == 32  # Batch size
        assert len(gradients) == len(list(fed_ap_worker.model.parameters()))  # Number of model parameters

        # Perform another training step to test cumulative behavior
        _, num_sample = fed_ap_worker.train_step(gradients, cur_steps=1, train_steps=2)
        assert num_sample == 64  # Cumulative batch size over two steps

