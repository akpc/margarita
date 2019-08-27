from openvqe.circuit._gates_impl import QGateImpl
import numpy


class QCircuit():

    def __init__(self, weight=1.0, gates=None):
        if gates is None:
            self.gates = []
        else:
            self.gates = gates
        self.weight = weight

    def __getitem__(self, item):
        """
        iteration over gates is possible
        :param item:
        :return: returns the ith gate in the circuit where i=item
        """
        return self.gates[item]

    def __setitem__(self, key: int, value: QGateImpl):
        """
        Insert a gate at a specific position
        :param key:
        :param value:
        :return: self for chaining
        """
        self.gates[key] = value
        return self

    def dagger(self):
        """
        Sumner's Fork:
        I have changed this so that the call to dagger is just dagger all the way down.
        :return: Circuit in reverse with signs of rotations switched
        """
        result = QCircuit()
        for g in reversed(self.gates):
            result += g.dagger()
        return result

    def __true_weight__(self):
        '''
        returns the true weight of the circuit, taking in both the weight assigned by the user and and the weight of all the gates
        '''
        pass

    def replace_gate(self, position, gates: list, inplace: bool = False):
        '''
        if inplace=False:
        returns a transformed version of the circuit in which whatever gate was at 'position' is removed and replaced with,
        in sequence, all the gates in in gates.
        else, changes swaps out the gate at position for the gates in gates, but does not return a new object.
        Particularly useful in the post-processing of gate gradients.

        '''
        prior = self.gates[:position]
        new = gates
        posterior = self.gates[position + 1:]
        #### note: this is gonna play badly with gates that would be applied simultaneously, I think.)
        new_gates = prior + new + posterior
        if inplace == False:
            return QCircuit(weight=self.weight, gates=new_gates)
        else:
            self.gates = new_gates

    def insert_gate(self, position: int, gate: QGateImpl):
        if position == "random":
            self.insert_gate_at_random_position(gate=gate)
        else:
            self.gates.insert(position, gate)
        return self

    def insert_gate_at_random_position(self, gate: QGateImpl):
        position = numpy.random.choice(len(self.gates), 1)[0]

        if isinstance(gate, QCircuit):
            for g in gate.gates:
                self.insert_gate(position=position, gate=g)
        else:
            self.insert_gate(position=position, gate=gate)

    def extract_parameters(self) -> list:
        """
        Extract the angles from the circuit
        :return: angles as list of tuples where each tuple contains the angle and the position of the gate in the circuit
        """
        parameters = []
        for i, g in enumerate(self.gates):
            if g.is_parametrized():
                if not g.is_frozen():
                    parameters.append((i, g.parameter))

        return parameters

    def change_angles(self, angles: list):
        """
        Change angles in of all parametrized gates in circuit
        inplace operation
        :param angles: list of tuples where the first entry is the position of the angle in the circuit and the second the angle itself
        :return: circuit itself for chaining
        """

        try:
            for a in angles:
                position = a[0]
                angle = a[1]
                if not self.gates[position].is_parametrized():
                    raise Exception("You are trying to change the angle of an unparametrized gate\ngate=" + str(
                        self.gates[position]) + "\nangles=(" + str(a) + ")")
                elif self.gates[position].is_frozen():
                    raise Exception("You are trying to change the angle of a frozen gate\ngate=" + str(
                        self.gates[position]) + "\nangles=(" + str(a) + ")")
                else:
                    self.gates[position].parameter = angle
        except IndexError as error:
            raise Exception(str(error) + "\nFailed to assign angles, you probably provided to much angles")
        except TypeError as error:
            raise Exception(str(
                error) + "\nFailed to assign angles, you have to give a list of tuples holding position in circuit and angle value")

        return self

    def max_qubit(self):
        qmax = 0
        for g in self.gates:
            qmax = max(qmax, g.max_qubit())
        return qmax

    def __add__(self, other):
        if isinstance(other, QGateImpl):
            other = self.wrap_gate(other)
        result = QCircuit()
        result.gates = (self.gates + other.gates).copy()
        return result

    def __iadd__(self, other):
        if isinstance(other, QGateImpl):
            other = self.wrap_gate(other)
        if isinstance(other, QGateImpl):
            self.gates.append(other)
        else:
            self.gates += other.gates
        return self

    def __str__(self):
        result = "circuit: "
        if self.weight != 1.0:
            result += " weight=" + "{:06.2f}".format(self.weight) + " \n"
        else:
            result += "\n"
        for g in self.gates:
            result += str(g) + "\n"
        return result

    def __eq__(self, other):
        if self.weight != other.weight:
            return False
        if len(self.gates) != len(other.gates):
            return False
        for i,g in enumerate(self.gates):
            if g != other.gates[i]:
                return False
        return True

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def wrap_gate(gate: QGateImpl):
        """
        :param gate: Abstract Gate
        :return: wrap gate in QCircuit structure (enable arithmetic operators)
        """
        if isinstance(gate, QCircuit):
            return gate
        else:
            return QCircuit(gates=[gate])

    def recompile_gate(self, gate):
        """
        TODO:
        remove
        Recompiles gates based on the instruction function
        :param gate: the QGate to recompile
        :return: list of tuple of lists of qgates
        """
        recompiled_gates = []
        for g in self.gates:
            recompiled_gates.append(instruction(g))
        return QCircuit(gates=recompiled_gates)
