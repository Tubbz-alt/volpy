import numpy as np
from sympy import symbols
from sympy import integrate
from scipy.spatial import Delaunay
import pandas as pd
import plotly
import plotly.offline as po
import plotly.graph_objs as go
from plotly import tools

from .coordinates import CartesianCoordinate
from .utils import print_progress

class Line2D():
    """A 2-Dimensional line"""
    def __init__(self,
                 point_A: CartesianCoordinate,
                 point_B: CartesianCoordinate):
        """Constructor

        Arguments:
        point_A: Cartesian Coordinate for point A
        point_B: Cartesian Coordinate for point B
        """
        self.point_A = point_A
        self.point_B = point_B

    def get_line_equation(self):
        """Returns a callable f(x): the line equation that connects point_A to
        point_B
        """
        if self.point_B.x - self.point_A.x == 0: # line parallel to the y axis
            return None
        else:
            slope = (self.point_B.y - self.point_A.y) /\
                    (self.point_B.x - self.point_A.x)
            linear_constant = -slope*self.point_A.x + self.point_A.y
            x = symbols('x')
            return slope*x + linear_constant

class Triangle():
    """A triangle in a 3D Cartesian Coordinates System"""
    def __init__(self,
                 point_A: CartesianCoordinate,
                 point_B: CartesianCoordinate,
                 point_C: CartesianCoordinate):
        self.point_A = point_A
        self.point_B = point_B
        self.point_C = point_C

    def get_plane_equation(self):
        """
        Returns the plane equation constants for the plane that contains points
        A, B and C.
        Plane equation: a*(x-xo) + b*(y-yo) + c*(z-zo) = 0
        """
        vector_AB = self.point_B - self.point_A
        vector_BC = self.point_C - self.point_B
        normal_vector = np.cross(vector_AB, vector_BC)
        a = normal_vector[0]
        b = normal_vector[1]
        c = normal_vector[2]
        xo = self.point_A.x
        yo = self.point_A.y
        zo = self.point_A.z
        x, y = symbols('x y') # z = f(x, y)
        return ((-a*(x-xo)-b*(y-yo))/c)+zo

    def get_volume(self):
        """
        Returns the volume from the polyhedron generated by triangle ABC and
        the XY plane
        """
        plane = self.get_plane_equation()
        # Define how to compute a double integral
        def compute_double_integral(outer_boundary_from,
                                    outer_boundary_to,
                                    line_from_equation,
                                    line_to_equation):
            if ((line_from_equation is None) or (line_to_equation is None)):
                return 0.0 # vertical line
            x, y = symbols('x y')
            volume =  integrate(plane,
                                (y, line_from_equation, line_to_equation),
                                (x, outer_boundary_from, outer_boundary_to))
            return volume

        # Instantiate lines. Points are sorted on the x coordinate.
        points = [self.point_A, self.point_B, self.point_C]
        points.sort()
        sorted_point_A, sorted_point_B, sorted_point_C = points
        lineAB = Line2D(sorted_point_A, sorted_point_B)
        lineBC = Line2D(sorted_point_B, sorted_point_C)
        lineAC = Line2D(sorted_point_A, sorted_point_C)

        # Compute double integral 1:
        volume1 = compute_double_integral(sorted_point_A.x,
                                          sorted_point_B.x,
                                          lineAC.get_line_equation(),
                                          lineAB.get_line_equation())
        # Compute double integral 2:
        volume2 = compute_double_integral(sorted_point_B.x,
                                          sorted_point_C.x,
                                          lineAC.get_line_equation(),
                                          lineBC.get_line_equation())

        # Sum and return
        total_volume = abs(volume1) + abs(volume2)
        return total_volume

class TriangularMesh(object):

    def __init__(self, point_cloud, ref_level=0.0):
        """
        :param point_cloud: a pandas dataframe containing x, y, z, elevation
        :attr data: a numpy array representing the triangular mesh of points
                    generated using a Delaunay triangulation.
                    Not set by the user.
        """
        self.point_cloud = point_cloud
        self.data = Delaunay(point_cloud[['x', 'y']]).simplices
        self._flat_volume = {0.0: 0.0} # dictionary containing ref_level and 
        # corresponding flat volume. Used by the cut and fill routines.
        # Defined as an attribute to reduce the need to recalculate
        # CONSIDER CREATING additional dictionaries to allow faster performance on new calculations for the same point_cloud
        self.triangular_areas = len(self.data)

    def get_volume(self, data_points='Default', show_progress=True):
        """
        Returns the volume.

        :param data_points: (pandas DataFrame) a subset of the point_cloud 
                            parameter that initializes with this class. The 
                            reason it is given as an input is to reuse this 
                            get_volume method to calculate cut and fill volumes.
                            (default) the hole point_cloud.
        :param show_progress: (bool) shows the progress bar when True.
        """
        if type(data_points) is not pd.core.frame.DataFrame: 
            data_points=self.point_cloud
        
        data = Delaunay(data_points[['x', 'y']]).simplices # I think I can remove this. Do it after done with the corresponding cut/fill unit tests.
        mesh_volume = 0
        iteration = 0
        data_amount = len(data)
        for i in range(data_amount):
            A = data_points.iloc[data[i][0]]
            B = data_points.iloc[data[i][1]]
            C = data_points.iloc[data[i][2]]
            point_A = CartesianCoordinate(A['x'], A['y'], A['z'])
            point_B = CartesianCoordinate(B['x'], B['y'], B['z'])
            point_C = CartesianCoordinate(C['x'], C['y'], C['z'])
            triangle = Triangle(point_A, point_B, point_C)
            volume = triangle.get_volume()
            mesh_volume += volume
            
            # update progress bar
            if show_progress:
                iteration += 1
                print_progress(iteration,
                            data_amount,
                            prefix='Progress:',
                            suffix='Complete',
                            length = 50)
        return mesh_volume

    def _get_flat_volume(self, ref_level):
        """
        Sets the internal attribute for flat_volume.
        """
        data_flat = self.point_cloud.copy(deep=True)
        data_flat['z'] = ref_level
        self._flat_volume[ref_level] = self.get_volume(
            data_flat, show_progress=False)

    def get_cut_volume(self, ref_level, show_progress=True):
        """
        Returns the terrain fill volume, corresponding to the amount of volume
        required to fill the terrain up to the ref_level

        :param ref_level: the reference level to be used. This is relative to
        the lowest point available in z.
        """
        data_cut = self.point_cloud.copy(deep=True)
        data_cut.loc[data_cut['z'] < ref_level, 'z'] = ref_level
        if ref_level not in self._flat_volume.keys():
            self._get_flat_volume(ref_level)
        flat_volume = self._flat_volume[ref_level]
        full_cut = self.get_volume(data_cut, show_progress=show_progress)
        return np.int64(full_cut - flat_volume)

    def get_fill_volume(self, ref_level, show_progress=True):
        """
        Returns the terrain fill volume, corresponding to the amount of volume
        required to fill the terrain up to the ref_level

        :param ref_level: the reference level to be used. This is relative to
        the lowest point available in z.
        """
        if ref_level == 0.0: return 0.0 # quick exit when ref is 0.0.
        
        data_fill = self.point_cloud.copy(deep=True)
        data_fill.loc[data_fill['z'] >= ref_level, 'z'] = ref_level
        if ref_level not in self._flat_volume.keys():
            self._get_flat_volume(ref_level)
        flat_volume = self._flat_volume[ref_level]
        full_fill = self.get_volume(data_fill, show_progress=show_progress)
        return np.int64(flat_volume - full_fill)


    # Create TEST CASES for cut and fill volumes. Keep in mind how you are
    # flattening the projection to make sure the numbers match.

    def get_volume_curves(self, step=0.5, swell_factor=1.0):
        """
        Returns a pandas DataFrame representing containing the following 
        columns:
        1. ref_level
        2. cut volume
        3. fill_volume
        4. swell_cut_volume
        This can be used to plot required cut/fill volumes to flatten the 
        surveyed terrain at varing ref_levels.

        :param step: the increase in ref_level at each iteration
        :param swell_factor: 
        """
        z_max = self.point_cloud['z'].max()
        z_min = 0
        levels = np.arange(z_min, z_max, step)

        iterations = len(levels)-1
        iteration = 0
        curves = []

        integrals = self.triangular_areas * 3 * iterations
        print("Please hold while I calculate {} double integrals.".format(
            integrals))

        for ref_level in levels:
            cut = self.get_cut_volume(ref_level, show_progress=False)
            fill = self.get_fill_volume(ref_level, show_progress=False)
            swell_cut = cut / swell_factor
            curves.append([ref_level, cut, fill, swell_cut])
            print_progress(iteration,
                           iterations,
                           prefix='Progress:',
                           suffix='Complete',
                           length = 50)
            iteration += 1

        columns = ['ref_level', 'cut', 'fill', 'swell_cut']
        return pd.DataFrame(data=curves, columns=columns)

    def plot_curves(self, curves):
        """
        Plots a 2D graph with the volume curves.

        :param curves: (pandas DataFrame) a collection of volume curves data.
                       Expected columns: ref_level, cut, fill, swell_cut
        """
        layout = go.Layout(title='Volume Curves', autosize=True)
        def get_trace(volume, name):
            return go.Scatter(x=curves['ref_level'],
                              y=volume,
                              mode='lines',
                              name=name)

        trace_cut = get_trace(curves['cut'], 'cut')
        trace_fill = get_trace(curves['fill'], 'fill')
        trace_swell_cut = get_trace(curves['swell_cut'], 'usable cut')

        figure = go.Figure(data=[trace_cut, trace_fill, trace_swell_cut],
                           layout=layout)
        return po.plot(figure, filename='volume_curves.html')