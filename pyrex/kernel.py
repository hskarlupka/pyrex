"""Module for the simulation kernel. Includes neutrino generation,
ray tracking (no raytracing yet), and hit generation."""

import numpy as np
from pyrex.internal_functions import normalize
from pyrex.signals import AskaryanSignal
from pyrex.ray_tracing import PathFinder, ReflectedPathFinder


class EventKernel:
    """Kernel for generation of events with a given particle generator,
    ice model, and list of antennas."""
    def __init__(self, generator, ice_model, antennas):
        self.gen = generator
        self.ice = ice_model
        self.ant_array = antennas

    def event(self):
        """Generate particle, propagate signal through ice to antennas,
        process signal at antennas, and return the original particle."""
        p = self.gen.create_particle()
        n = self.ice.index(p.vertex[2])
        for ant in self.ant_array:
            pf = PathFinder(self.ice, p.vertex, ant.position)
            rpf = ReflectedPathFinder(self.ice, p.vertex, ant.position)

            for path in [pf, rpf]:
                # If path is invalid, skip it
                if not(path.exists):
                    continue

                # p.direction and k should both be unit vectors
                # epol is (negative) vector rejection of k onto p.direction
                k = path.received_ray
                epol = normalize(np.vdot(k, p.direction) * k - p.direction)
                # In case k and p.direction are equal
                # (antenna directly on shower axis), just let epol be all zeros

                psi = np.arccos(np.vdot(p.direction, path.emitted_ray))
                # TODO: Support angles larger than pi/2
                if psi>np.pi/2:
                    continue

                times = np.linspace(-20e-9, 80e-9, 2048, endpoint=False)
                pulse = AskaryanSignal(times=times, energy=p.energy,
                                       theta=psi, n=n)

                path.propagate(pulse)
                # Dividing by path length scales Askaryan pulse properly
                pulse.values /= path.path_length

                ant.receive(pulse, origin=p.vertex, polarization=epol)

        return p
