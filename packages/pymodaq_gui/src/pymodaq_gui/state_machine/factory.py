from pymodaq_gui.state_machine.statemachine import StateMachine

class StateMachineFactory:

    """A class to construct a sequencer state machine from a yaml file.

    The yaml definition is parsed in an iterative loop for states and
    transitions between these. Actions to be performed upon entering a state
    are not evaluated here. This has to be done when setting up the sequencer.
    """

    @classmethod
    def from_yaml(cls, yaml_data):
        """Create a StateMachine instance from yaml-formatted data.

        Returns the state machine.
        """
        state_machine = StateMachine()
        transitions = {}
        for i,data in enumerate(yaml_data['states']):
            cls._state_from_yaml(data, state_machine, i==0, state_machine,
                                 transitions)
        cls._make_transitions(state_machine, yaml_data['states'])
        return state_machine

    @classmethod
    def _state_from_yaml(cls, yaml_data, parent_state, is_initial,
                         state_machine, transitions):
        name = yaml_data['name']
        is_final = yaml_data['final'] if 'final' in yaml_data else False
        current_state = \
            state_machine.add_state(name, is_initial, is_final, parent_state)

        if is_final:
            assert 'states' not in yaml_data
            assert 'actions' not in yaml_data
            assert 'transitions' not in yaml_data
        else:
            if 'states' in yaml_data:
                for i,data in enumerate(yaml_data['states']):
                    cls._state_from_yaml(data, current_state, i==0,
                                         state_machine, transitions)

    @classmethod
    def _make_transitions(cls, state_machine, states):
        for state in states:
            if 'transitions' in state:
                for transition in state['transitions']:
                    state_machine.add_transition(state['name'],
                                                 transition['target'],
                                                 transition['event'])
            if 'states' in state:
                cls._make_transitions(state_machine, state['states'])
