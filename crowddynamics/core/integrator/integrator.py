import numba
import numpy as np
from numba import f8

from crowddynamics.core.structures.agents import agent_type_three_circle
from crowddynamics.core.vector.vector2D import length_nx2, wrap_to_pi


@numba.jit([f8(f8, f8, f8[:, :], f8[:, :])],
           nopython=True, nogil=True, cache=True)
def adaptive_timestep(dt_min, dt_max, velocity, target_velocity):
    r"""
    Timestep is selected from interval :math:`[\Delta t_{min}, \Delta t_{max}]`
    by bounding the maximum step size :math:`\Delta x` an agent can take per
    iteration cycle, obtained from

    .. math::
       \Delta x = c \Delta t_{max} \max_{i\in A} v_i^0 \\

    where

    - :math:`c > 0` is scaling coefficient
    - :math:`v_i^0` is agent's target velocity
    - :math:`\max_{i\in A} v_i^0` is the maximum of all target velocities

    Timestep is then obtained from

    .. math::
       \Delta t_{mid} &= \frac{\Delta x}{\max_{i \in A} v_i} \\
       \Delta t &=
       \begin{cases}
       \Delta t_{min} & \Delta t_{mid} < \Delta t_{min} \\
       \Delta t_{mid} &  \\
       \Delta t_{max} & \Delta t_{mid} > \Delta t_{max} \\
       \end{cases}

    where

    - :math:`v_i` is agent's current velocity


    Args:
        dt_min:
            Minimum timestep :math:`\Delta x_{min}` for adaptive integration.

        dt_max:
            Maximum timestep :math:`\Delta x_{max}` for adaptive integration.

        velocity:

        target_velocity:

    Returns:
        float:

    References

    https://en.wikipedia.org/wiki/Adaptive_stepsize
    """
    v_max = np.max(length_nx2(velocity))
    if v_max == 0.0:
        return dt_max
    c = 1.1
    dx_max = c * np.max(target_velocity) * dt_max
    dt = dx_max / v_max
    if dt > dt_max:
        return dt_max
    elif dt < dt_min:
        return dt_min
    else:
        return dt


# TODO: numba generated jit
def euler_integration(agent, dt_min, dt_max):
    r"""
    Differential system is integrated using numerical integration scheme using
    discrete adaptive timestep :math:`\Delta t`.

    Acceleration on an agent

    .. math::
       a_{k} &= \mathbf{f}_{k} / m \\
       \mathbf{x}_{k+1} &= \mathbf{x}_{k} + \mathbf{v}_{k} \Delta t + \frac{1}{2} a_{k} \Delta t^{2} \\
       \mathbf{v}_{k+1} &= \mathbf{v}_{k} + a_{k} \Delta t \\

    Angular acceleration

    .. math::
       \alpha_{k} &= M_{k} / I \\
       \varphi_{k+1} &= \varphi_{k} + \omega_{k} \Delta t + \frac{1}{2} \alpha_{k} \Delta t^{2} \\
       \omega_{k+1} &= \omega_{k} + \alpha_{k} \Delta t \\

    Args:
        agent (Agent):

        dt_min (float):
            Minimum timestep :math:`\Delta x_{min}` for adaptive integration.

        dt_max (float):
            Maximum timestep :math:`\Delta x_{max}` for adaptive integration.

    Returns:
        float: Timestep :math:`\Delta t` that was used for integration.

    """
    # Time step selection
    dt = adaptive_timestep(dt_min, dt_max, agent['velocity'], agent['target_velocity'])

    # Updating agents
    acceleration = agent['force'] / agent['mass']
    agent['position'] += agent['velocity'] * dt + acceleration / 2 * dt ** 2
    agent['velocity'] += acceleration * dt

    if agent.dtype is agent_type_three_circle:
        angular_acceleration = agent['torque'] / agent['inertia_rot']
        agent['orientation'] += agent['angular_velocity'] * dt + angular_acceleration / 2 * dt ** 2
        agent['angular_velocity'] += angular_acceleration * dt
        agent['orientation'][:] = wrap_to_pi(agent['orientation'])

    return dt


def velocity_verlet(agent, dt_min, dt_max):
    r"""
    Velocity verlet

    .. math::
        \mathbf{v}_{k+1/2} &= \mathbf{v}_{k} + \frac{1}{2} a_{k} \Delta t \\
        \mathbf{x}_{k+1} &= \mathbf{x}_{k} + \mathbf{v}_{k+1/2} \Delta t \\
        a_{k+1} &= \mathbf{f}_{k+1} / m \\
        \mathbf{v}_{k+1} &= \mathbf{v}_{k+1/2} + \frac{1}{2} a_{k+1} \Delta t

    References

    https://en.wikipedia.org/wiki/Verlet_integration#Velocity_Verlet

    Args:
        agent (Agent):

        dt_min (float):
            Minimum timestep :math:`\Delta x_{min}` for adaptive integration.

        dt_max (float):
            Maximum timestep :math:`\Delta x_{max}` for adaptive integration.

    Yields:
        float: Timestep :math:`\Delta t` that was used for integration.

    """
    # TODO: save old accelerations to agent structure
    dt = adaptive_timestep(dt_min, dt_max, agent['velocity'], agent['target_velocity'])
    acceleration = agent['force'] / agent['mass']
    agent['position'] += agent['velocity'] * dt + acceleration / 2 * dt ** 2
    yield dt

    while True:
        dt = adaptive_timestep(dt_min, dt_max, agent['velocity'], agent['target_velocity'])
        new_acceleration = agent['force'] / agent['mass']
        agent['velocity'] += (acceleration + new_acceleration) / 2 * dt
        agent['position'] += agent['velocity'] * dt + new_acceleration / 2 * dt ** 2
        acceleration = new_acceleration
        yield dt
