import unittest
import pandas as pd
import numpy as np
from pysd import utils

test_model = 'test-models/samples/teacup/teacup.mdl'
test_model_subs = 'test-models/tests/subscript_2d_arrays/test_subscript_2d_arrays.mdl'


class TestPySD(unittest.TestCase):
    def test_run(self):
        import pysd
        model = pysd.read_vensim(test_model)
        stocks = model.run()
        self.assertTrue(isinstance(stocks, pd.DataFrame))  # return a dataframe
        self.assertTrue('Teacup Temperature' in stocks.columns.values)  # contains correct column
        self.assertGreater(len(stocks), 3)  # has multiple rows
        self.assertTrue(stocks.notnull().all().all())  # there are no null values in the set

    def test_run_includes_last_value(self):
        import pysd
        model = pysd.read_vensim(test_model)
        res = model.run()
        self.assertEqual(res.index[-1], model.components.final_time())

    def test_run_build_timeseries(self):
        import pysd
        model = pysd.read_vensim(test_model)

        model.components.initial_time = lambda: 3
        model.components.final_time = lambda: 7
        model.components.time_step = lambda: 1
        model.initialize()

        res = model.run()

        actual = list(res.index)
        expected = [3., 4., 5., 6., 7.]
        self.assertSequenceEqual(actual, expected)

    def test_run_return_timestamps(self):
        """Addresses https://github.com/JamesPHoughton/pysd/issues/17"""
        import pysd
        model = pysd.read_vensim(test_model)
        timestamps = np.random.rand(5).cumsum()
        stocks = model.run(return_timestamps=timestamps)
        self.assertTrue((stocks.index.values == timestamps).all())

        stocks = model.run(return_timestamps=5)
        self.assertEqual(stocks.index[0], 5)

    def test_run_return_timestamps_past_final_time(self):
        """ If the user enters a timestamp that is longer than the euler
        timeseries that is defined by the normal model file, should
        extend the euler series to the largest timestamp"""
        import pysd
        model = pysd.read_vensim(test_model)
        return_timestamps = list(range(0, 100, 10))
        stocks = model.run(return_timestamps=return_timestamps)
        self.assertSequenceEqual(return_timestamps, list(stocks.index))

    def test_return_timestamps_with_range(self):
        """
        Tests that return timestamps may receive a 'range'.
        It will be cast to a numpy array in the end...
        """
        import pysd
        model = pysd.read_vensim(test_model)
        return_timestamps = range(0, 100, 10)
        stocks = model.run(return_timestamps=return_timestamps)
        self.assertSequenceEqual(return_timestamps, list(stocks.index))

    def test_run_return_columns_original_names(self):
        """Addresses https://github.com/JamesPHoughton/pysd/issues/26
        - Also checks that columns are returned in the correct order"""
        import pysd
        model = pysd.read_vensim(test_model)
        return_columns = ['Room Temperature', 'Teacup Temperature']
        result = model.run(return_columns=return_columns)
        self.assertEqual(set(result.columns), set(return_columns))

    def test_run_reload(self):
        """ Addresses https://github.com/JamesPHoughton/pysd/issues/99"""
        import pysd
        model = pysd.read_vensim(test_model)
        result0 = model.run()
        result1 = model.run(params={'Room Temperature': 1000})
        result2 = model.run()
        result3 = model.run(reload=True)

        self.assertTrue((result0 == result3).all().all())
        self.assertFalse((result0 == result1).all().all())
        self.assertTrue((result1 == result2).all().all())

    def test_run_return_columns_pysafe_names(self):
        """Addresses https://github.com/JamesPHoughton/pysd/issues/26"""
        import pysd
        model = pysd.read_vensim(test_model)
        return_columns = ['room_temperature', 'teacup_temperature']
        result = model.run(return_columns=return_columns)
        self.assertEqual(set(result.columns), set(return_columns))

    def test_initial_conditions_tuple_pysafe_names(self):
        import pysd
        model = pysd.read_vensim(test_model)
        stocks = model.run(initial_condition=(3000, {'teacup_temperature': 33}),
                           return_timestamps=list(range(3000, 3010)))
        self.assertEqual(stocks.index[0], 3000)
        self.assertEqual(stocks['Teacup Temperature'].iloc[0], 33)

    def test_initial_conditions_tuple_original_names(self):
        """ Responds to https://github.com/JamesPHoughton/pysd/issues/77"""
        import pysd
        model = pysd.read_vensim(test_model)
        stocks = model.run(initial_condition=(3000, {'Teacup Temperature': 33}),
                           return_timestamps=list(range(3000, 3010)))
        self.assertEqual(stocks.index[0], 3000)
        self.assertEqual(stocks['Teacup Temperature'].iloc[0], 33)

    def test_initial_conditions_current(self):
        import pysd
        model = pysd.read_vensim(test_model)
        stocks1 = model.run(return_timestamps=list(range(0, 31)))
        stocks2 = model.run(initial_condition='current',
                            return_timestamps=list(range(30, 45)))
        self.assertEqual(stocks1['Teacup Temperature'].iloc[-1],
                         stocks2['Teacup Temperature'].iloc[0])

    def test_initial_condition_bad_value(self):
        import pysd
        model = pysd.read_vensim(test_model)
        with self.assertRaises(ValueError):
            model.run(initial_condition='bad value')

    def test_initial_conditions_subscripted_value_with_constant(self):
        import xarray as xr
        import pysd

        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']
        output = xr.DataArray([[5, 5], [5, 5], [5, 5]], coords, dims)

        model = pysd.read_vensim(test_model_subs)
        res = model.run(initial_condition=(5, {'initial_values': 5}),
                        return_columns=['Initial Values'],
                        return_timestamps=list(range(5, 10)))
        self.assertTrue(output.equals(res['Initial Values'].iloc[0]))
        self.assertEqual(res.index[0], 5)

    def test_initial_conditions_subscripted_value_with_partial_xarray(self):
        import xarray as xr
        import pysd

        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']
        output = xr.DataArray([[5, 3], [5, 3], [5, 3]], coords, dims)
        input_val = xr.DataArray([5, 3],
            {'Second Dimension Subscript': ['Column 1', 'Column 2']},
            ['Second Dimension Subscript'])

        model = pysd.read_vensim(test_model_subs)
        res = model.run(initial_condition=(5, {'Initial Values': input_val}),
                        return_columns=['Initial Values'],
                        return_timestamps=list(range(5, 10)))
        self.assertTrue(output.equals(res['Initial Values'].iloc[0]))
        self.assertEqual(res.index[0], 5)

    def test_initial_conditions_subscripted_value_with_xarray(self):
        import xarray as xr
        import pysd

        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']
        output = xr.DataArray([[5, 3], [4, 8], [9, 3]], coords, dims)

        model = pysd.read_vensim(test_model_subs)
        res = model.run(initial_condition=(5, {'initial_values': output}),
                        return_columns=['Initial Values'],
                        return_timestamps=list(range(5, 10)))
        self.assertTrue(output.equals(res['Initial Values'].iloc[0]))
        self.assertEqual(res.index[0], 5)

    def test_initial_conditions_subscripted_value_with_numpy(self):
        # test for backward compatibility to remove in the future
        import warnings
        import xarray as xr
        import pysd

        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']
        output = xr.DataArray([[5, 3], [4, 8], [9, 3]], coords, dims)
        input_ = np.array([[5, 3], [4, 8], [9, 3]])

        model = pysd.read_vensim(test_model_subs)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            res = model.run(initial_condition=(5, {'initial_values': input_}),
                            return_columns=['Initial Values'],
                            return_timestamps=list(range(5, 10)))
        self.assertTrue(output.equals(res['Initial Values'].iloc[0]))
        self.assertEqual(res.index[0], 5)
        self.assertEqual(len(w), 1)
        self.assertTrue(
            'deprecated' in str(w[0].message))

    def test_set_constant_parameter(self):
        """ In response to: re: https://github.com/JamesPHoughton/pysd/issues/5"""
        import pysd
        model = pysd.read_vensim(test_model)
        model.set_components({'room_temperature': 20})
        self.assertEqual(model.components.room_temperature(), 20)

        model.run(params={'room_temperature': 70})
        self.assertEqual(model.components.room_temperature(), 70)

    def test_set_timeseries_parameter(self):
        import pysd
        model = pysd.read_vensim(test_model)
        timeseries = list(range(30))
        temp_timeseries = pd.Series(index=timeseries,
                                    data=(50 + np.random.rand(len(timeseries)).cumsum()))
        res = model.run(params={'room_temperature': temp_timeseries},
                        return_columns=['room_temperature'],
                        return_timestamps=timeseries)
        self.assertTrue((res['room_temperature'] == temp_timeseries).all())

    def test_set_component_with_real_name(self):
        import pysd
        model = pysd.read_vensim(test_model)
        model.set_components({'Room Temperature': 20})
        self.assertEqual(model.components.room_temperature(), 20)

        model.run(params={'Room Temperature': 70})
        self.assertEqual(model.components.room_temperature(), 70)

    def test_set_components_warnings(self):
        """Addresses https://github.com/JamesPHoughton/pysd/issues/80"""
        import pysd
        import warnings
        model = pysd.read_vensim(test_model)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            model.set_components({'Teacup Temperature': 20,
                                  'Characteristic Time': 15})  # set stock value using params
        self.assertEqual(len(w), 1)
        self.assertTrue(
            'Teacup Temperature' in str(w[0].message))  # check that warning references the stock

    def test_set_components_with_function(self):
        def test_func():
            return 5

        import pysd
        model = pysd.read_vensim(test_model)
        model.set_components({'Room Temperature': test_func})
        res = model.run(return_columns=['Room Temperature'])
        self.assertEqual(test_func(), res['Room Temperature'].iloc[0])

    def test_set_subscripted_value_with_constant(self):
        import xarray as xr
        import pysd

        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']
        output = xr.DataArray([[5, 5], [5, 5], [5, 5]], coords, dims)

        model = pysd.read_vensim(test_model_subs)
        model.set_components({'initial_values': 5, 'final_time': 10})
        res = model.run(return_columns=['Initial Values'])
        self.assertTrue(output.equals(res['Initial Values'].iloc[0]))

    def test_set_subscripted_value_with_partial_xarray(self):
        import xarray as xr
        import pysd

        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']
        output = xr.DataArray([[5, 3], [5, 3], [5, 3]], coords, dims)
        input_val = xr.DataArray([5, 3],
            {'Second Dimension Subscript': ['Column 1', 'Column 2']},
            ['Second Dimension Subscript'])

        model = pysd.read_vensim(test_model_subs)
        model.set_components({'Initial Values': input_val, 'final_time': 10})
        res = model.run(return_columns=['Initial Values'])
        self.assertTrue(output.equals(res['Initial Values'].iloc[0]))

    def test_set_subscripted_value_with_xarray(self):
        import xarray as xr
        import pysd

        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']
        output = xr.DataArray([[5, 3], [4, 8], [9, 3]], coords, dims)

        model = pysd.read_vensim(test_model_subs)
        model.set_components({'initial_values': output, 'final_time': 10})
        res = model.run(return_columns=['Initial Values'])
        self.assertTrue(output.equals(res['Initial Values'].iloc[0]))

    def test_set_subscripted_value_with_numpy(self):
        # test for backward compatibility to remove in the future
        import warnings
        import xarray as xr
        import pysd

        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']
        output = xr.DataArray([[5, 3], [4, 8], [9, 3]], coords, dims)
        input_ = np.array([[5, 3], [4, 8], [9, 3]])

        model = pysd.read_vensim(test_model_subs)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            model.set_components({'initial_values': input_, 'final_time': 10})
        res = model.run(return_columns=['Initial Values'])
        self.assertTrue(output.equals(res['Initial Values'].iloc[0]))
        self.assertEqual(len(w), 1)
        self.assertTrue(
            'deprecated' in str(w[0].message))

    def test_set_subscripted_timeseries_parameter_with_constant(self):
        import xarray as xr
        import pysd

        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']

        model = pysd.read_vensim(test_model_subs)
        timeseries = list(range(10))
        val_series = [50 + rd for rd in
                      np.random.rand(len(timeseries)).cumsum()]
        xr_series = [xr.DataArray([[val,val],[val,val],[val,val]], coords, dims)
                     for val in val_series]

        temp_timeseries = pd.Series(index=timeseries,
                                    data=val_series)
        res = model.run(params={'initial_values': temp_timeseries, 'final_time': 10},
                        return_columns=['initial_values'],
                        return_timestamps=timeseries)

        self.assertTrue(np.all([r.equals(t) for r,t in
            zip(res['initial_values'].values, xr_series)]))

    def test_set_subscripted_timeseries_parameter_with_partial_xarray(self):
        import xarray as xr
        import pysd

        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']
        out_b = xr.DataArray([[0, 0], [0, 0], [0, 0]], coords, dims)
        input_val = xr.DataArray([5, 3],
            {'Second Dimension Subscript': ['Column 1', 'Column 2']},
            ['Second Dimension Subscript'])

        model = pysd.read_vensim(test_model_subs)
        timeseries = list(range(10))
        val_series = [input_val + rd for rd in
                      np.random.rand(len(timeseries)).cumsum()]
        temp_timeseries = pd.Series(index=timeseries,
                                    data=val_series)
        out_series = [out_b + val
                     for val in val_series]
        model.set_components({'initial_values': temp_timeseries, 'final_time': 10})
        res = model.run(return_columns=['initial_values'])
        self.assertTrue(np.all([r.equals(t) for r,t in
            zip(res['initial_values'].values, out_series)]))


    def test_set_subscripted_timeseries_parameter_with_xarray(self):
        import xarray as xr
        import pysd

        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']

        init_val = xr.DataArray([[5, 3], [4, 8], [9, 3]], coords, dims)

        model = pysd.read_vensim(test_model_subs)
        timeseries = list(range(10))
        temp_timeseries = pd.Series(index=timeseries,
                                    data=[init_val + rd for rd in
                                          np.random.rand(len(timeseries)).cumsum()])
        res = model.run(params={'initial_values': temp_timeseries, 'final_time': 10},
                        return_columns=['initial_values'],
                        return_timestamps=timeseries)

        self.assertTrue(np.all([r.equals(t) for r,t in
            zip(res['initial_values'].values, temp_timeseries.values)]))

    def test_docs(self):
        """ Test that the model prints some documentation """
        import pysd
        model = pysd.read_vensim(test_model)
        self.assertIsInstance(str(model), str)  # tests string conversion of model

        doc = model.doc()
        self.assertIsInstance(doc, pd.DataFrame)
        self.assertSetEqual({'Characteristic Time', 'Teacup Temperature',
                             'FINAL TIME', 'Heat Loss to Room', 'INITIAL TIME',
                             'Room Temperature', 'SAVEPER', 'TIME STEP'},
                            set(doc['Real Name'].values))

        self.assertEqual(doc[doc['Real Name'] == 'Heat Loss to Room']['Unit'].values[0],
                         'Degrees Fahrenheit/Minute')
        self.assertEqual(doc[doc['Real Name'] == 'Teacup Temperature']['Py Name'].values[0],
                         'teacup_temperature')
        self.assertEqual(doc[doc['Real Name'] == 'INITIAL TIME']['Comment'].values[0],
                         'The initial time for the simulation.')
        self.assertEqual(doc[doc['Real Name'] == 'Characteristic Time']['Type'].values[0],
                         'constant')

    def test_docs_multiline_eqn(self):
        """ Test that the model prints some documentation """
        import pysd

        path2model = 'test-models/tests/multiple_lines_def/'\
                     + 'test_multiple_lines_def.mdl'
        model = pysd.read_vensim(path2model)

        doc = model.doc()

        self.assertEqual(doc[doc['Real Name'] == 'price']['Unit'].values[0],
                         'euros/kg')
        self.assertEqual(doc[doc['Real Name'] == 'price']['Py Name'].values[0],
                         'price')
        self.assertTrue(doc[doc['Real Name'] == 'price']['Subs'].values[0] in
                        ["['fruits']", "[u'fruits']"])
        self.assertEqual(doc[doc['Real Name'] == 'price']['Eqn'].values[0],
                         '1.2; .; .; .; 1.4')


    def test_stepwise_cache(self):
        # Checks backward compatibility, must be changed to @cache.step when deprecated
        run_history = []
        result_history = []

        global time
        time = lambda: 0  # for testing cache function
        from pysd.py_backend.functions import cache

        cache.time = time()

        @cache('step')
        def upstream(run_hist, res_hist):
            run_hist.append('U')
            return 'up'

        def downstream(run_hist, res_hist):
            run_hist.append('D')
            result_history.append(upstream(run_hist, res_hist))
            return 'down'

        # initially neither function has a chache value
        self.assertFalse('upstream' in cache.data['step'])
        self.assertFalse('downstream' in cache.data['step'])

        # when the functions are called,
        # the cache is instantiated in the upstream (cached) function
        result_history.append(downstream(run_history, result_history))
        self.assertTrue('upstream' in cache.data['step'])
        self.assertFalse('upstream' in cache.data['run'])
        self.assertFalse('downstream' in cache.data['step'])
        self.assertEqual(cache.time, 0)
        self.assertListEqual(run_history, ['D', 'U'])
        self.assertListEqual(result_history, ['up', 'down'])

        # cleaning only run cache shouldn't affect the step cache
        cache.clean('run')
        self.assertTrue('upstream' in cache.data['step'])

        # at the second call, the uncached function is run,
        # but the cached upstream function returns its prior value
        result_history.append(downstream(run_history, result_history))
        self.assertEqual(cache.time, 0)
        self.assertListEqual(run_history, ['D', 'U', 'D'])
        self.assertListEqual(result_history, ['up', 'down', 'up', 'down'])

        # when the time is reset, both functions are run again.
        time = lambda: 2
        cache.reset(time())

        result_history.append(downstream(run_history, result_history))
        self.assertEqual(cache.time, 2)
        self.assertListEqual(run_history, ['D', 'U', 'D', 'D', 'U'])
        self.assertListEqual(result_history,
                             ['up', 'down', 'up', 'down', 'up', 'down'])

    def test_runwise_cache(self):
        # Checks backward compatibility, must be changed to @cache.run when deprecated
        run_history = []
        result_history = []

        global time
        time = lambda: 0  # for testing cache function
        from pysd.py_backend.functions import cache

        cache.time = time()

        @cache('run')
        def upstream(run_hist, res_hist):
            run_hist.append('U')
            return 'up'

        def downstream(run_hist, res_hist):
            run_hist.append('D')
            result_history.append(upstream(run_hist, res_hist))
            return 'down'

        # initially neither function has a chache value
        self.assertFalse('upstream' in cache.data['run'])
        self.assertFalse('downstream' in cache.data['run'])

        # when the functions are called,
        # the cache is instantiated in the upstream (cached) function
        result_history.append(downstream(run_history, result_history))
        self.assertEqual(cache.time, 0)
        self.assertTrue('upstream' in cache.data['run'])
        self.assertFalse('upstream' in cache.data['step'])
        self.assertFalse('downstream' in cache.data['run'])
        self.assertListEqual(run_history, ['D', 'U'])
        self.assertListEqual(result_history, ['up', 'down'])

        # cleaning only step cache shouldn't affect the step cache
        cache.clean('step')
        self.assertTrue('upstream' in cache.data['run'])

        # at the second call, the uncached function is run,
        # but the cached upstream function returns its prior value
        result_history.append(downstream(run_history, result_history))
        self.assertEqual(cache.time, 0)
        self.assertListEqual(run_history, ['D', 'U', 'D'])
        self.assertListEqual(result_history, ['up', 'down', 'up', 'down'])

        # when the time is reset, this has no impact on the upstream cache.
        time = lambda: 2
        cache.reset(time())

        result_history.append(downstream(run_history, result_history))
        self.assertEqual(cache.time, 2)
        self.assertListEqual(run_history, ['D', 'U', 'D', 'D'])
        self.assertListEqual(result_history,
                             ['up', 'down', 'up', 'down', 'up', 'down'])

    def test_initialize(self):
        import pysd
        model = pysd.read_vensim(test_model)
        initial_temp = model.components.teacup_temperature()
        model.run()
        final_temp = model.components.teacup_temperature()
        model.initialize()
        reset_temp = model.components.teacup_temperature()
        self.assertNotEqual(initial_temp, final_temp)
        self.assertEqual(initial_temp, reset_temp)

    def test_reset_state(self):
        import pysd
        import warnings
        model = pysd.read_vensim(test_model)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            model.reset_state()
        self.assertEqual(len(w), 1)

    def test_set_state(self):
        import pysd
        model = pysd.read_vensim(test_model)

        initial_temp = model.components.teacup_temperature()
        initial_time = model.components.time()

        new_time = np.random.rand()

        # Test that we can set with real names
        model.set_state(new_time, {'Teacup Temperature': 500})
        self.assertNotEqual(initial_temp, 500)
        self.assertEqual(model.components.teacup_temperature(), 500)

        # Test setting with pysafe names
        model.set_state(new_time + 1, {'teacup_temperature': 202})
        self.assertEqual(model.components.teacup_temperature(), 202)

        # Test setting with stateful object name
        model.set_state(new_time + 2, {'_integ_teacup_temperature': 302})
        self.assertEqual(model.components.teacup_temperature(), 302)

    def test_set_state_subscripted_value_with_constant(self):
        import xarray as xr
        import pysd

        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']
        output_b = xr.DataArray([[0, 0], [0, 0], [0, 0]], coords, dims)

        new_time = np.random.rand()

        model = pysd.read_vensim(test_model_subs)
        initial_stock = model.components.stock_a()
        initial_time = model.components.time()

        # Test that we can set with real names
        model.set_state(new_time, {'Stock A': 500})
        self.assertFalse(initial_stock.equals(output_b + 500))
        self.assertTrue(model.components.stock_a().equals(output_b + 500))

        # Test setting with pysafe names
        model.set_state(new_time + 1, {'stock_a': 202})
        self.assertTrue(model.components.stock_a().equals(output_b + 202))

        # Test setting with stateful object name
        model.set_state(new_time + 2, {'_integ_stock_a': 302})
        self.assertTrue(model.components.stock_a().equals(output_b + 302))


    def test_set_state_subscripted_value_with_partial_xarray(self):
        import xarray as xr
        import pysd

        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']
        output1 = xr.DataArray([[5, 3], [5, 3], [5, 3]], coords, dims)
        input_val1 = xr.DataArray([5, 3],
            {'Second Dimension Subscript': ['Column 1', 'Column 2']},
            ['Second Dimension Subscript'])

        output2 = xr.DataArray([[55, 33], [55, 33], [55, 33]], coords, dims)
        input_val2 = xr.DataArray([55, 33],
            {'Second Dimension Subscript': ['Column 1', 'Column 2']},
            ['Second Dimension Subscript'])

        output3 = xr.DataArray([[40, 20], [40, 20], [40, 20]], coords, dims)
        input_val3 = xr.DataArray([40, 20],
            {'Second Dimension Subscript': ['Column 1', 'Column 2']},
            ['Second Dimension Subscript'])

        new_time = np.random.rand()

        model = pysd.read_vensim(test_model_subs)
        initial_stock = model.components.stock_a()

        # Test that we can set with real names
        model.set_state(new_time, {'Stock A': input_val1})
        self.assertFalse(initial_stock.equals(output1))
        self.assertTrue(model.components.stock_a().equals(output1))

        # Test setting with pysafe names
        model.set_state(new_time + 1, {'stock_a': input_val2})
        self.assertTrue(model.components.stock_a().equals(output2))

        # Test setting with stateful object name
        model.set_state(new_time + 2, {'_integ_stock_a': input_val3})
        self.assertTrue(model.components.stock_a().equals(output3))

    def test_set_state_subscripted_value_with_xarray(self):
        import xarray as xr
        import pysd

        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']
        output1 = xr.DataArray([[5, 3], [4, 8], [9, 3]], coords, dims)
        output2 = xr.DataArray([[53, 43], [84, 80], [29, 63]], coords, dims)
        output3 = xr.DataArray([[54, 32], [40, 87], [93, 93]], coords, dims)

        new_time = np.random.rand()

        model = pysd.read_vensim(test_model_subs)
        initial_stock = model.components.stock_a()

        # Test that we can set with real names
        model.set_state(new_time, {'Stock A': output1})
        self.assertFalse(initial_stock.equals(output1))
        self.assertTrue(model.components.stock_a().equals(output1))

        # Test setting with pysafe names
        model.set_state(new_time + 1, {'stock_a': output2})
        self.assertTrue(model.components.stock_a().equals(output2))

        # Test setting with stateful object name
        model.set_state(new_time + 2, {'_integ_stock_a': output3})
        self.assertTrue(model.components.stock_a().equals(output3))

    def test_set_state_subscripted_value_with_numpy(self):
            # test for backward compatibility to remove in the future
        import warnings
        import xarray as xr
        import pysd
        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']
        output1 = xr.DataArray([[5, 3], [4, 8], [9, 3]], coords, dims)
        input1 = np.array([[5, 3], [4, 8], [9, 3]])
        output2 = xr.DataArray([[53, 43], [84, 80], [29, 63]], coords, dims)
        input2 = np.array([[53, 43], [84, 80], [29, 63]])
        output3 = xr.DataArray([[54, 32], [40, 87], [93, 93]], coords, dims)
        input3 = np.array([[54, 32], [40, 87], [93, 93]])

        new_time = np.random.rand()

        model = pysd.read_vensim(test_model_subs)
        initial_stock = model.components.stock_a()

        # Test that we can set with real names
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            model.set_state(new_time, {'Stock A': input1})
        self.assertFalse(initial_stock.equals(output1))
        self.assertTrue(model.components.stock_a().equals(output1))
        self.assertEqual(len(w), 1)
        self.assertTrue(
            'deprecated' in str(w[0].message))

        # Test setting with pysafe names
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            model.set_state(new_time + 1, {'stock_a': input2})
        self.assertTrue(model.components.stock_a().equals(output2))
        self.assertEqual(len(w), 1)
        self.assertTrue(
            'deprecated' in str(w[0].message))

        # Test setting with stateful object name
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            model.set_state(new_time + 2, {'_integ_stock_a': input3})
        self.assertTrue(model.components.stock_a().equals(output3))
        self.assertEqual(len(w), 1)
        self.assertTrue(
            'deprecated' in str(w[0].message))

    def test_replace_element(self):
        import pysd
        model = pysd.read_vensim(test_model)
        stocks1 = model.run()
        model.components.characteristic_time = lambda: 3
        stocks2 = model.run()
        self.assertGreater(stocks1['Teacup Temperature'].loc[10],
                           stocks2['Teacup Temperature'].loc[10])

    def test_set_initial_condition_origin_full(self):
        import pysd
        model = pysd.read_vensim(test_model)
        initial_temp = model.components.teacup_temperature()
        initial_time = model.components.time()

        new_state = {'Teacup Temperature': 500}
        new_time = 10

        model.set_initial_condition((new_time, new_state))
        set_temp = model.components.teacup_temperature()
        set_time = model.components.time()

        self.assertNotEqual(set_temp, initial_temp, "Test definition is wrong, please change configuration")
        self.assertEqual(set_temp, 500)

        self.assertNotEqual(initial_time, new_time, "Test definition is wrong, please change configuration")
        self.assertEqual(new_time, set_time)

        model.set_initial_condition('original')
        set_temp = model.components.teacup_temperature()
        set_time = model.components.time()

        self.assertEqual(initial_temp, set_temp)
        self.assertEqual(initial_time, set_time)

    def test_set_initial_condition_origin_short(self):
        import pysd
        model = pysd.read_vensim(test_model)
        initial_temp = model.components.teacup_temperature()
        initial_time = model.components.time()

        new_state = {'Teacup Temperature': 500}
        new_time = 10

        model.set_initial_condition((new_time, new_state))
        set_temp = model.components.teacup_temperature()
        set_time = model.components.time()

        self.assertNotEqual(set_temp, initial_temp, "Test definition is wrong, please change configuration")
        self.assertEqual(set_temp, 500)

        self.assertNotEqual(initial_time, new_time, "Test definition is wrong, please change configuration")
        self.assertEqual(new_time, set_time)

        model.set_initial_condition('o')
        set_temp = model.components.teacup_temperature()
        set_time = model.components.time()

        self.assertEqual(initial_temp, set_temp)
        self.assertEqual(initial_time, set_time)

    def test_set_initial_condition_for_stock_component(self):
        import pysd
        model = pysd.read_vensim(test_model)
        initial_temp = model.components.teacup_temperature()
        initial_time = model.components.time()

        new_state = {'Teacup Temperature': 500}
        new_time = 10

        model.set_initial_condition((new_time, new_state))
        set_temp = model.components.teacup_temperature()
        set_time = model.components.time()

        self.assertNotEqual(set_temp, initial_temp, "Test definition is wrong, please change configuration")
        self.assertEqual(set_temp, 500)

        self.assertNotEqual(initial_time, 10, "Test definition is wrong, please change configuration")
        self.assertEqual(set_time, 10)

    def test_set_initial_condition_for_constant_component(self):
        import pysd
        model = pysd.read_vensim(test_model)
        initial_temp = model.components.teacup_temperature()
        initial_time = model.components.time()

        new_state = {'Room Temperature': 100}
        new_time = 10

        model.set_initial_condition((new_time, new_state))
        set_temp = model.components.room_temperature()
        set_time = model.components.time()

        self.assertNotEqual(set_temp, initial_temp, "Test definition is wrong, please change configuration")
        self.assertEqual(set_temp, 100)

        self.assertNotEqual(initial_time, 10, "Test definition is wrong, please change configuration")
        self.assertEqual(set_time, 10)

    #TODO
    def test_get_coords(self):
        import pysd

        coords = {'One Dimensional Subscript': ['Entry 1', 'Entry 2', 'Entry 3'],
                  'Second Dimension Subscript': ['Column 1', 'Column 2']}
        dims = ['One Dimensional Subscript', 'Second Dimension Subscript']

        coords_dims = (coords, dims)

        model = pysd.read_vensim(test_model)
        model2 = pysd.read_vensim(test_model_subs)

        self.assertIsNone(model.get_coords('Room Temperature'))
        self.assertIsNone(model.get_coords('room_temperature'))
        self.assertIsNone(model.get_coords('teacup_temperature'))
        self.assertIsNone(model.get_coords('_integ_teacup_temperature'))

        self.assertEqual(model2.get_coords('Initial Values'), coords_dims)
        self.assertEqual(model2.get_coords('initial_values'), coords_dims)
        self.assertEqual(model2.get_coords('Stock A'), coords_dims)
        self.assertEqual(model2.get_coords('stock_a'), coords_dims)
        self.assertEqual(model2.get_coords('_integ_stock_a'), coords_dims)


    def test__build_euler_timeseries(self):
        import pysd
        model = pysd.read_vensim(test_model)
        model.components.initial_time = lambda: 3
        model.components.final_time = lambda: 10
        model.components.time_step = lambda: 1
        model.initialize()

        actual = list(model._build_euler_timeseries(return_timestamps=[10]))
        expected = range(3, 11, 1)
        self.assertSequenceEqual(actual, expected)

    def test__integrate(self):
        import pysd
        # Todo: think through a stronger test here...
        model = pysd.read_vensim(test_model)
        res = model._integrate(time_steps=list(range(5)),
                               capture_elements=['teacup_temperature'],
                               return_timestamps=list(range(0, 5, 2)))
        self.assertIsInstance(res, list)
        self.assertIsInstance(res[0], dict)

    def test_default_returns_with_construction_functions(self):
        """
        If the run function is called with no arguments, should still be able
        to get default return functions.

        """
        import pysd
        model = pysd.read_vensim('test-models/tests/delays/test_delays.mdl')
        ret = model.run()
        self.assertTrue({'Initial Value',
                         'Input',
                         'Order Variable',
                         'Output Delay1',
                         'Output Delay1I',
                         'Output Delay3'} <=
                        set(ret.columns.values))

    def test_default_returns_with_lookups(self):
        """
        Addresses https://github.com/JamesPHoughton/pysd/issues/114
        The default settings should skip model elements with no particular
        return value
        """
        import pysd
        model = pysd.read_vensim('test-models/tests/lookups/test_lookups.mdl')
        ret = model.run()
        self.assertTrue({'accumulation',
                         'rate',
                         'lookup function call'} <=
                        set(ret.columns.values))

    def test_py_model_file(self):
        """Addresses https://github.com/JamesPHoughton/pysd/issues/86"""
        import pysd
        model = pysd.read_vensim(test_model)
        self.assertEqual(model.py_model_file, test_model.replace('.mdl', '.py'))

    def test_mdl_file(self):
        """Relates to https://github.com/JamesPHoughton/pysd/issues/86"""
        import pysd
        model = pysd.read_vensim(test_model)
        self.assertEqual(model.mdl_file, test_model)

    @unittest.skip('infinite loop')
    def test_incomplete_model(self):
        import pysd
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            model = pysd.read_vensim(
                'test-models/tests/incomplete_equations/test_incomplete_model.mdl')
        self.assertTrue(any([warn.category == SyntaxWarning for warn in w]))

        with warnings.catch_warnings(record=True) as w:
            model.run()
        self.assertEqual(len(w), 1)


class TestModelInteraction(unittest.TestCase):
    """ The tests in this class test pysd's interaction with itself
        and other modules. """

    def test_multiple_load(self):
        """
        Test that we can load and run multiple models at the same time,
        and that the models don't interact with each other. This can
        happen if we arent careful about class attributes vs instance attributes

        This test responds to issue:
        https://github.com/JamesPHoughton/pysd/issues/23

        """
        import pysd

        model_1 = pysd.read_vensim('test-models/samples/teacup/teacup.mdl')
        model_2 = pysd.read_vensim('test-models/samples/SIR/SIR.mdl')

        self.assertNotIn('teacup_temperature', dir(model_2.components))
        self.assertIn('susceptible', dir(model_2.components))

        self.assertNotIn('susceptible', dir(model_1.components))
        self.assertIn('teacup_temperature', dir(model_1.components))

    def test_no_crosstalk(self):
        """
        Need to check that if we instantiate two copies of the same model,
        changes to one copy do not influence the other copy.

        Checks for issue: https://github.com/JamesPHoughton/pysd/issues/108
        that time is not shared between the two models

        """
        # Todo: this test could be made more comprehensive
        import pysd

        model_1 = pysd.read_vensim('test-models/samples/teacup/teacup.mdl')
        model_2 = pysd.read_vensim('test-models/samples/SIR/SIR.mdl')

        model_1.components.initial_time = lambda: 10
        self.assertNotEqual(model_2.components.initial_time, 10)

        # check that the model time is not shared between the two objects
        model_1.run()
        self.assertNotEqual(model_1.time(), model_2.time())

    def test_restart_cache(self):
        """
        Test that when we cache a model variable at the 'run' time,
         if the variable is changed and the model re-run, the cache updates
         to the new variable, instead of maintaining the old one.
        """
        import pysd
        model = pysd.read_vensim(test_model)
        model.run()
        old = model.components.room_temperature()
        model.set_components({'Room Temperature': 345})
        new = model.components.room_temperature()
        model.run()
        self.assertEqual(new, 345)
        self.assertNotEqual(old, new)


class TestMultiRun(unittest.TestCase):
    def test_delay_reinitializes(self):
        import pysd
        model = pysd.read_vensim('../tests/test-models/tests/delays/test_delays.mdl')
        res1 = model.run()
        res2 = model.run()
        self.assertTrue(all(res1 == res2))
