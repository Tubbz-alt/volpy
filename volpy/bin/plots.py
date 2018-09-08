import plotly
import plotly.offline as po
import plotly.graph_objs as go
from plotly import tools

class SurveyPlot():
    """Groups different plot types on  data"""

    def __init__(self, survey):
        """
        Initializer

        Arguments:
        survey: an instance of Survey
        """
        self.survey = survey

    def scatter3d(self, x, y, z, name):
        layout = go.Layout(title='3D View', autosize=True)
        trace = go.Scatter3d(x=x,
                             y=y,
                             z=z,
                             mode='markers',
                             marker=dict(size=4,
                                         line=dict(color='#fff3ff',
                                                   width=0.5),
                                         opacity=0.8),
                             connectgaps=False,
                             name=name)

        figure = go.Figure(data=[trace], layout=layout)
        return po.plot(figure, filename='3d_view.html')

    def scatter(self, x, y, name):
        trace = go.Scatter(
            x=x,
            y=y,
            name=name,
            mode='markers',
            marker=dict(
                size=4,
                opacity=0.8
            ),
            connectgaps=False)
        return trace

    def histogram(self, x, name):
        trace = go.Histogram(x=x,
                             name=name,
                             histfunc='count',
                             marker=dict(color='#ffb800'))
        return trace

    def generate_subplots(self):
        figure = tools.make_subplots(rows=2,
                                     cols=2,
                                     subplot_titles=('Histogram',
                                                     'Top View: XY',
                                                     'Elevation(m): XZ',
                                                     'Elevation(m): YZ'))
        figure['layout'].update(title='Survey plots')
        trace3d = self.scatter3d(self.survey.data.x,
                                 self.survey.data.y,
                                 self.survey.data.z,
                                 '3D View')
        trace_histogram = self.histogram(self.survey.data.z, 'Elevation Histogram')
        trace_top = self.scatter(self.survey.data.x,
                                 self.survey.data.y,
                                 'Top View')
        trace_xz = self.scatter(self.survey.data.x,
                                self.survey.data.z,
                                'XZ')
        trace_yz = self.scatter(self.survey.data.y,
                                self.survey.data.z,
                                'YZ')
        figure.append_trace(trace_histogram, 1, 1)
        figure.append_trace(trace_top, 1, 2)
        figure.append_trace(trace_xz, 2, 1)
        figure.append_trace(trace_yz, 2, 2)
        return po.plot(figure, filename='survey_subplots.html')
