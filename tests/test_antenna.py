"""File containing tests of pyrex antenna module"""

import pytest

from pyrex.antenna import Antenna, DipoleAntenna
from pyrex.signals import Signal
from pyrex.ice_model import IceModel

import numpy as np



@pytest.fixture
def antenna():
    """Fixture for forming basic Antenna object"""
    return Antenna(position=[0,0,-250], temperature=300,
                   freq_range=[500e6, 750e6], resistance=100)

@pytest.fixture
def dipole():
    """Fixture for forming basic DipoleAntenna object"""
    return DipoleAntenna(name="ant", position=[0,0,-250],
                         center_frequency=250e6, bandwidth=300e6,
                         resistance=100, orientation=[0,0,1],
                         trigger_threshold=75e-6)


class TestAntenna:
    """Tests for Antenna class"""
    def test_creation(self, antenna):
        """Test that the antenna's creation goes as expected"""
        assert np.array_equal(antenna.position, [0,0,-250])
        assert np.array_equal(antenna.z_axis, [0,0,1])
        assert np.array_equal(antenna.x_axis, [1,0,0])
        assert antenna.antenna_factor == 1
        assert antenna.efficiency == 1
        assert np.array_equal(antenna.freq_range, [500e6, 750e6])
        assert antenna.temperature == 300
        assert antenna.resistance == 100
        assert antenna.noisy

    def test_is_hit(self, antenna):
        """Test that is_hit is true when there is a signal and false otherwise"""
        assert not(antenna.is_hit)
        antenna.signals.append(Signal([0],[0]))
        assert antenna.is_hit

    def test_is_hit_not_writable(self, antenna):
        """Test that is_hit cannot be assigned to"""
        with pytest.raises(AttributeError):
            antenna.is_hit = True

    def test_clear(self, antenna):
        """Test that clear emptys signals list"""
        antenna.signals.append(Signal([0],[0]))
        antenna.clear()
        assert antenna.signals == []

    def test_default_trigger(self, antenna):
        """Test that the antenna triggers on empty signal"""
        assert antenna.trigger(Signal([0],[0]))

    def test_default_response(self, antenna):
        """Test that the frequency response is always 1"""
        assert np.array_equal(antenna.response(np.logspace(0,10)), np.ones(50))

    def test_default_directional_gain(self, antenna):
        """Test that the directional gain is always 1"""
        thetas = np.linspace(0, np.pi, 7)
        phis = np.linspace(0, 2*np.pi, 13)
        gains = []
        for theta in thetas:
            for phi in phis:
                gains.append(antenna.directional_gain(theta, phi))
        assert np.array_equal(gains, np.ones(7*13))

    def test_default_polarization_gain(self, antenna):
        """Test that the polarization gain is always 1"""
        xs = np.linspace(0, 1, 3)
        ys = np.linspace(0, 1, 3)
        zs = np.linspace(0, 1, 3)
        gains = []
        for x in xs:
            for y in ys:
                for z in zs:
                    gains.append(antenna.polarization_gain((x,y,z)))
        assert np.array_equal(gains, np.ones(3**3))

    def test_receive(self, antenna):
        """Test that the antenna properly receives signals"""
        antenna.receive(Signal([0,1e-9,2e-9], [0,1,0], Signal.ValueTypes.voltage))
        assert len(antenna.signals) > 0

    def test_no_waveforms(self, antenna):
        """Test that waveforms returns an empty list if there are no signals"""
        assert antenna.waveforms == []

    def test_waveforms_exist(self, antenna):
        """Test that waveforms returns a waveform when a signal has been received"""
        antenna.receive(Signal([0,1e-9,2e-9], [0,1,0], Signal.ValueTypes.voltage))
        assert antenna.waveforms != []
        assert isinstance(antenna.waveforms[0], Signal)
        assert antenna._noises != []
        assert antenna._triggers == [True]

    def test_delay_noise_calculation(self, antenna):
        """Test that antenna noise isn't calculated until it is needed"""
        antenna.receive(Signal([0,1e-9,2e-9], [0,1,0], Signal.ValueTypes.voltage))
        assert antenna._noises == []
        antenna.waveforms
        assert antenna._noises != []

    def test_noises_not_recalculated(self, antenna):
        """Test that noise signals aren't recalculated every time"""
        antenna.signals.append(Signal([0],[1]))
        waveforms1 = antenna.waveforms
        noises1 = antenna._noises
        waveforms2 = antenna.waveforms
        noises2 = antenna._noises
        assert noises1 == noises2

    def test_no_trigger_no_waveform(self, antenna):
        """Test that signals which don't trigger don't appear in waveforms,
        but do appear in all_waveforms"""
        antenna.trigger = lambda signal: False
        antenna.signals.append(Signal([0],[1]))
        assert antenna.is_hit == False
        assert antenna.waveforms == []
        assert antenna.all_waveforms != []

    def test_noise_master_generation(self, antenna):
        """Test that _noise_master is generated the first time make_noise is
        called and never again"""
        assert antenna._noise_master is None
        noise = antenna.make_noise(np.linspace(0, 100e-9))
        assert antenna._noise_master is not None
        old_noise_master = antenna._noise_master
        noise = antenna.make_noise(np.linspace(0, 50e-9))
        assert antenna._noise_master == old_noise_master



class TestDipoleAntenna:
    """Tests for DipoleAntenna class"""
    def test_creation(self, dipole):
        """Test that the antenna's creation goes as expected"""
        assert dipole.name == "ant"
        assert np.array_equal(dipole.position, [0,0,-250])
        assert np.array_equal(dipole.z_axis, [0,0,1])
        assert dipole.x_axis[2] == 0
        assert dipole.antenna_factor == 2 * 250e6 / 3e8
        assert dipole.efficiency == 1
        assert np.array_equal(dipole.freq_range, [100e6, 400e6])
        assert dipole.temperature == pytest.approx(IceModel.temperature(-250))
        assert dipole.resistance == 100
        assert dipole.threshold == 75e-6
        assert dipole.noisy

    @pytest.mark.parametrize("freq", np.arange(50, 500, 50)*1e6)
    def test_frequency_response(self, dipole, freq):
        """Test that the frequency response of the dipole antenna is as
        expected"""
        response = dipole.response(freq)
        db_point = 1/np.sqrt(2)
        if (freq==pytest.approx(dipole.freq_range[0])
                or freq==pytest.approx(dipole.freq_range[1])):
            assert np.abs(response) == pytest.approx(db_point, rel=0.01)
        elif freq>dipole.freq_range[0] and freq<dipole.freq_range[1]:
            assert np.abs(response) > db_point
            assert np.abs(response) <= 1
        else:
            assert np.abs(response) < db_point

    @pytest.mark.parametrize("theta", np.linspace(0, np.pi, 7))
    @pytest.mark.parametrize("phi", np.linspace(0, 2*np.pi, 13))
    def test_directional_gain(self, dipole, theta, phi):
        """Test that the directional gain of the dipole antenna goes as sin"""
        assert dipole.directional_gain(theta, phi) == pytest.approx(np.sin(theta))

    @pytest.mark.parametrize("x", np.linspace(0, 1, 3))
    @pytest.mark.parametrize("y", np.linspace(0, 1, 3))
    @pytest.mark.parametrize("z", np.linspace(0, 1, 11))
    def test_polarization_gain(self, dipole, x, y, z):
        """Test that the polarization gain of the dipole antenna goes as the
        dot product of the antenna axis with the polarization direction
        (i.e. the z-component)"""
        assert dipole.polarization_gain((x,y,z)) == pytest.approx(z)
