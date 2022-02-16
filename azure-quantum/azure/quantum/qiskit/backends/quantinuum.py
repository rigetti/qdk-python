##
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
##
from typing import TYPE_CHECKING, Union, List
from azure.quantum.version import __version__
from azure.quantum.qiskit.job import AzureQuantumJob

try:
    from qiskit import QuantumCircuit
    from qiskit.providers import BackendV1 as Backend
    from qiskit.providers.models import BackendConfiguration
    from qiskit.providers import Options
    from qiskit.qobj import Qobj, QasmQobj

except ImportError:
    raise ImportError(
    "Missing optional 'qiskit' dependencies. \
To install run: pip install azure-quantum[qiskit]"
)

if TYPE_CHECKING:
    from azure.quantum.qiskit import AzureQuantumProvider

import logging
logger = logging.getLogger(__name__)

__all__ = [
    "QuantinuumBackend",
    "QuantinuumQPUBackend",
    "QuantinuumAPIValidatorBackend",
    "QuantinuumSimulatorBackend"
]

HONEYWELL_BASIS_GATES = [
    "x",
    "y",
    "z",
    "rx",
    "ry",
    "rz",
    "h",
    "cx",
    "ccx",
    "cz",
    "s",
    "sdg",
    "t",
    "tdg",
    "v",
    "vdg",
    "zz",
    "measure",
    "reset"
]


class QuantinuumBackend(Backend):
    """Base class for interfacing with a Quantinuum backend in Azure Quantum"""

    @classmethod
    def _default_options(cls):
        return Options(count=500)

    def estimate_cost(self, circuit: QuantumCircuit, count: int):
        """Estimate cost for running this circuit

        :param circuit: Qiskit quantum circuit
        :type circuit: QuantumCircuit
        :param count: Shot count
        :type count: int
        """
        input_data = circuit.qasm()
        workspace = self.provider().get_workspace()
        target = workspace.get_targets(self.name())
        return target.estimate_cost(input_data, num_shots=count)

    def run(self, circuit: Union[QuantumCircuit, List[QuantumCircuit]], **kwargs):
        """Submits the given circuit for execution on a Quantinuum target."""
        # Some Qiskit features require passing lists of circuits, so unpack those here.
        # We currently only support single-experiment jobs.
        if isinstance(circuit, (list, tuple)):
            if len(circuit) > 1:
                raise NotImplementedError("Multi-experiment jobs are not supported!")
            circuit = circuit[0]

        # If the circuit was created using qiskit.assemble,
        # disassemble into QASM here
        if isinstance(circuit, QasmQobj) or isinstance(circuit, Qobj):
            from qiskit.assembler import disassemble
            circuits, run, _ = disassemble(circuit)
            circuit = circuits[0]
            if kwargs.get("count") is None:
                # Note that the default number of shots for QObj is 1024
                # unless the user specifies the backend.
                kwargs["count"] = run["shots"]

        input_data = circuit.qasm()

        # Options are mapped to input_params
        # Take also into consideration options passed in the kwargs, as the take precedence
        # over default values:
        input_params = vars(self.options)
        for opt in kwargs.copy():
            if opt in input_params:
                input_params[opt] = kwargs.pop(opt)

        logger.info(f"Submitting new job for backend {self.name()}")
        job = AzureQuantumJob(
            backend=self,
            name=circuit.name,
            target=self.name(),
            input_data=input_data,
            blob_name="inputData",
            content_type="application/qasm",
            provider_id="quantinuum",
            input_data_format="honeywell.openqasm.v1",
            output_data_format="honeywell.quantum-results.v1",
            input_params = input_params,
            metadata={ "qubits": str(circuit.num_qubits) },
            **kwargs
        )
        
        logger.info(f"Submitted job with id '{job.id()}' for circuit '{circuit.name}':")
        logger.info(input_data)

        return job


class QuantinuumAPIValidatorBackend(QuantinuumBackend):
    backend_names = (
        "quantinuum.hqs-lt-s1-apival",
        "quantinuum.hqs-lt-s2-apival"
    )

    def __init__(
        self,
        name: str,
        provider: "AzureQuantumProvider",
        **kwargs
    ):
        default_config = BackendConfiguration.from_dict(
            {
                "backend_name": name,
                "backend_version": __version__,
                "simulator": True,
                "local": False,
                "coupling_map": None,
                "description": "Quantinuum API validator on Azure Quantum",
                "basis_gates": HONEYWELL_BASIS_GATES,
                "memory": False,
                "n_qubits": 10,
                "conditional": False,
                "max_shots": 1,
                "max_experiments": 1,
                "open_pulse": False,
                "gates": [{"name": "TODO", "parameters": [], "qasm_def": "TODO"}],
            }
        )
        configuration: BackendConfiguration = kwargs.pop("configuration", default_config)
        logger.info("Initializing QuantinuumAPIValidatorBackend")
        super().__init__(configuration=configuration, provider=provider, **kwargs)


class QuantinuumSimulatorBackend(QuantinuumBackend):
    backend_names = (
        "quantinuum.hqs-lt-s1-sim",
        "quantinuum.hqs-lt-s2-sim"
    )

    def __init__(
        self,
        name: str,
        provider: "AzureQuantumProvider",
        **kwargs
    ):
        configuration: BackendConfiguration = kwargs.pop("configuration", None)
        default_config = BackendConfiguration.from_dict(
            {
                "backend_name": name,
                "backend_version": __version__,
                "simulator": True,
                "local": False,
                "coupling_map": None,
                "description": "Quantinuum simulator on Azure Quantum",
                "basis_gates": HONEYWELL_BASIS_GATES,
                "memory": False,
                "n_qubits": 10,
                "conditional": False,
                "max_shots": 1,
                "max_experiments": 1,
                "open_pulse": False,
                "gates": [{"name": "TODO", "parameters": [], "qasm_def": "TODO"}],
            }
        )
        configuration: BackendConfiguration = kwargs.pop("configuration", default_config)
        logger.info("Initializing QuantinuumAPIValidatorBackend")
        super().__init__(configuration=configuration, provider=provider, **kwargs)


class QuantinuumQPUBackend(QuantinuumBackend):
    backend_names = (
        "quantinuum.hqs-lt-s1",
        "quantinuum.hqs-lt-s2"
    )

    def __init__(
        self,
        name: str,
        provider: "AzureQuantumProvider",
        **kwargs
    ):
        default_config = BackendConfiguration.from_dict(
            {
                "backend_name": name,
                "backend_version": __version__,
                "simulator": False,
                "local": False,
                "coupling_map": None,
                "description": "Quantinuum QPU on Azure Quantum",
                "basis_gates": HONEYWELL_BASIS_GATES,
                "memory": False,
                "n_qubits": 10,
                "conditional": False,
                "max_shots": 10000,
                "max_experiments": 1,
                "open_pulse": False,
                "gates": [{"name": "TODO", "parameters": [], "qasm_def": "TODO"}],
            }
        )
        configuration: BackendConfiguration = kwargs.pop("configuration", default_config)
        logger.info("Initializing QuantinuumQPUBackend")
        super().__init__(configuration=configuration, provider=provider, **kwargs)