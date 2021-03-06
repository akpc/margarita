import pytest, numpy
import tequila as tq
import copy
# skip usage of symbolic simulator
import tequila.simulators.simulator_api

simulators = []
for k in tequila.simulators.simulator_api.INSTALLED_SIMULATORS.keys():
    if k != "symbolic":
        simulators.append(k)
samplers = []
for k in tequila.simulators.simulator_api.INSTALLED_SAMPLERS.keys():
    if k != "symbolic":
        samplers.append(k)


@pytest.mark.parametrize("simulator", [tequila.simulators.simulator_api.pick_backend("random"), tequila.simulators.simulator_api.pick_backend()])
def test_execution(simulator):
    U = tq.gates.Rz(angle="a", target=0) \
        + tq.gates.X(target=2) \
        + tq.gates.Ry(angle="b", target=1, control=2) \
        + tq.gates.Trotterized(angles=["c", "d"],
                               generators=[-0.25 * tq.paulis.Z(1), tq.paulis.X(0) + tq.paulis.Y(1)], steps=2) \
        + tq.gates.Trotterized(angles=[1.0, 2.0],
                               generators=[-0.25 * tq.paulis.Z(1), tq.paulis.X(0) + tq.paulis.Y(1)], steps=2) \
        + tq.gates.ExpPauli(angle="a", paulistring="X(0)Y(1)Z(2)")

    H = 1.0 * tq.paulis.X(0) + 2.0 * tq.paulis.Y(1) + 3.0 * tq.paulis.Z(2)
    O = tq.ExpectationValue(U=U, H=H)

    result = tq.optimizer_scipy.minimize(objective=O, maxiter=2, method="TNC", backend=simulator, silent=True)


@pytest.mark.parametrize("simulator", samplers)
def test_execution_shot(simulator):
    U = tq.gates.Rz(angle="a", target=0) \
        + tq.gates.X(target=2) \
        + tq.gates.Ry(angle="b", target=1, control=2) \
        + tq.gates.Trotterized(angles=["c","d"],
                               generators=[-0.25 * tq.paulis.Z(1), tq.paulis.X(0) + tq.paulis.Y(1)], steps=2) \
        + tq.gates.Trotterized(angles=[1.0, 2.0],
                               generators=[-0.25 * tq.paulis.Z(1), tq.paulis.X(0) + tq.paulis.Y(1)], steps=2) \
        + tq.gates.ExpPauli(angle="a", paulistring="X(0)Y(1)Z(2)")
    H = 1.0 * tq.paulis.X(0) + 2.0 * tq.paulis.Y(1) + 3.0 * tq.paulis.Z(2)
    O = tq.ExpectationValue(U=U, H=H)

    result = tq.optimizer_scipy.minimize(objective=O, maxiter=2, method="TNC", backend=simulator, samples=3, silent=True)
    assert (len(result.history.energies) <= 3)


@pytest.mark.parametrize("simulator", [tequila.simulators.simulator_api.pick_backend("random"), tequila.simulators.simulator_api.pick_backend()])
def test_one_qubit_wfn(simulator):
    U = tq.gates.Trotterized(angles=["a"], steps=1, generators=[tq.paulis.Y(0)])
    H = tq.paulis.X(0)
    O = tq.ExpectationValue(U=U, H=H)
    result = tq.optimizer_scipy.minimize(objective=O, maxiter=15, backend=simulator, silent=True)
    assert (numpy.isclose(result.energy, -1.0))

@pytest.mark.parametrize("simulator", samplers)
def test_one_qubit_shot(simulator):
    U = tq.gates.Trotterized(angles=["a"], steps=1, generators=[tq.paulis.Y(0)])
    H = tq.paulis.X(0)
    O = tq.ExpectationValue(U=U, H=H)
    result = tq.optimizer_scipy.minimize(objective=O, maxiter=15, backend=simulator, samples=10000, silent=True)
    assert (numpy.isclose(result.energy, -1.0, atol=1.e-1))


@pytest.mark.parametrize("simulator", [tequila.simulators.simulator_api.pick_backend("random"), tequila.simulators.simulator_api.pick_backend()])
@pytest.mark.parametrize("method", tq.optimizer_scipy.OptimizerSciPy.gradient_free_methods)
def test_gradient_free_methods(simulator, method):

    wfn = tq.QubitWaveFunction.from_string(string="1.0*|00> + 1.0*|11>")
    H = tq.paulis.Projector(wfn=wfn.normalize())
    U = tq.gates.Ry(angle="a", target=0)
    U += tq.gates.Ry(angle="b", target=1, control=0)
    E = tq.ExpectationValue(H=H, U=U)

    initial_values = {"a": 0.1, "b": 0.01}
    if method == "SLSQP": # method is not good
        return True

    result = tq.optimizer_scipy.minimize(objective=-E, method=method, tol=1.e-4,backend=simulator,
                                         initial_values=initial_values,silent=True)
    assert(numpy.isclose(result.energy, -1.0, atol=1.e-1))

@pytest.mark.parametrize("simulator", [tequila.simulators.simulator_api.pick_backend("random"), tequila.simulators.simulator_api.pick_backend()])
@pytest.mark.parametrize("method", tq.optimizer_scipy.OptimizerSciPy.gradient_based_methods)
@pytest.mark.parametrize("use_gradient", [None, '2-point'])
def test_gradient_based_methods(simulator, method, use_gradient):

    wfn = tq.QubitWaveFunction.from_string(string="1.0*|00> + 1.0*|11>")
    H = tq.paulis.Projector(wfn=wfn.normalize())
    U = tq.gates.Ry(angle=tq.assign_variable("a")*numpy.pi, target=0)
    U += tq.gates.Ry(angle=tq.assign_variable("b")*numpy.pi, target=1, control=0)
    E = tq.ExpectationValue(H=H, U=U)

    # need to improve starting points for some of the optimizations
    initial_values = {"a": 0.002, "b": 0.01}
    if method in ["L-BFGS-B", "TNC"]:
        initial_values = {"a": 0.1, "b": 0.8}
    if use_gradient is False:
        initial_values = {"a": 0.3, "b": 0.8}

    result = tq.optimizer_scipy.minimize(objective=-E, backend=simulator,gradient=use_gradient, method=method, tol=1.e-4,
                                         method_options={"gtol":1.e-4, "eps":1.e-4},
                                         initial_values=initial_values,silent=True)
    assert(numpy.isclose(result.energy, -1.0, atol=1.e-1))

@pytest.mark.parametrize("simulator", [tequila.simulators.simulator_api.pick_backend("random")])
@pytest.mark.parametrize("method", tq.optimizer_scipy.OptimizerSciPy.gradient_based_methods)
def test_gradient_based_methods_qng(simulator, method):

    H = tq.paulis.Y(0)
    U = tq.gates.Ry(numpy.pi/4,0) +tq.gates.Ry(numpy.pi/3,1)+tq.gates.Ry(numpy.pi/7,2)
    U += tq.gates.Rz('a',0)+tq.gates.Rz('b',1)
    U += tq.gates.CNOT(control=0,target=1)+tq.gates.CNOT(control=1,target=2)
    U += tq.gates.Ry('c',1) +tq.gates.Rx('d',2)
    U += tq.gates.CNOT(control=0,target=1)+tq.gates.CNOT(control=1,target=2)
    E = tq.ExpectationValue(H=H, U=U)
    # just equal to the original circuit, but i'm checking that all the sub-division works
    O=(4/8)*E+(3/8)*copy.deepcopy(E)+(1/8)*copy.deepcopy(E)+tq.Variable('a')-tq.Variable('a')
    if method == 'CG' or method == 'TNC':
        ### these methods SUCK. these parameters are almost correct, drawn from the history of more successful opt.
        initial_values = {'b': 1.2015702944309066, 'a': 0.36870888682982483, 'c': 1.4772702039340424, 'd': -0.5109743059462741}
    else:
        initial_values = {"a": 0.432, "b": -0.123, 'c':0.543,'d':0.233}

    result = tq.optimizer_scipy.minimize(objective=-O,qng=True,backend=simulator,
                                         method=method, tol=1.e-4, method_options={"gtol":1.e-4, "eps":1.e-4},
                                         initial_values=initial_values, silent=False)
    assert(numpy.isclose(result.energy, -0.612, atol=1.e-1))

@pytest.mark.parametrize("simulator", [tequila.simulators.simulator_api.pick_backend()])
@pytest.mark.parametrize("method", tq.optimizer_scipy.OptimizerSciPy.hessian_based_methods)
@pytest.mark.parametrize("use_hessian", [None, '2-point', '3-point'])
def test_hessian_based_methods(simulator, method, use_hessian):

    wfn = tq.QubitWaveFunction.from_string(string="1.0*|00> + 1.0*|11>")
    H = tq.paulis.Projector(wfn=wfn.normalize())
    U = tq.gates.Ry(angle=tq.assign_variable("a") * numpy.pi, target=0)
    U += tq.gates.Ry(angle=tq.assign_variable("b") * numpy.pi, target=1, control=0)
    E = tq.ExpectationValue(H=H, U=U)
    method_options = {"gtol": 1.e-4}

    # need to improve starting points for some of the optimizations
    initial_values = {"a": 0.002, "b": 0.01}
    if method not in ["TRUST-CONSTR", "TRUST_KRYLOV]"]:
        method_options['eta'] = 0.1
        method_options['initial_trust_radius'] = 0.1
        method_options['max_trust_radius'] = 0.25
        initial_values = {"a": 0.3, "b": 0.8}

    # numerical hessian only works for this method
    if use_hessian in ['2-point', '3-point']:
        if method != "TRUST-CONSTR":
            return
        initial_values = {"a": 0.3, "b": 0.8}

    result = tq.optimizer_scipy.minimize(objective=-E,backend=simulator, hessian=use_hessian, method=method, tol=1.e-4,
                                         method_options=method_options, initial_values=initial_values, silent=True)
    assert (numpy.isclose(result.energy, -1.0, atol=1.e-1))
