from model.enum import MlModel
from model.model_factory import MlModelFactory
from buld.utils import plot_selected, plot_histogram, data_normalize0, normalize3
from keras.utils import to_categorical
import numpy as np
from scipy import stats

class MlpTrading(object):
    def __init__(self, symbol) -> None:
        super().__init__()
        self.symbol = symbol
        self.names_input = ['nvo', 'mom5', 'mom10', 'mom20', 'mom50',       'range_sma', 'log_sma20', 'log_sma50', 'log_sma200', 'log_sma400',
                            # 'sma10', 'sma20', 'sma50', 'sma200', 'sma400', 'bb_hi10', 'bb_lo10',
                            # 'bb_hi20', 'bb_lo20', 'bb_hi50', 'bb_lo50', 'bb_hi200', 'bb_lo200'
                            'rel_bol_hi10',  'rel_bol_lo10', 'rel_bol_hi20', 'rel_bol_lo20', 'rel_bol_hi50', 'rel_bol_lo50',  'rel_bol_hi200', 'rel_bol_lo200',
                            'rsi10', 'rsi20', 'rsi50', 'rsi5',        'stoc10', 'stoc20', 'stoc50', 'stoc200', 'isPrev1Up', 'isPrev2Up']
        self.names_output2 = ['Green bar', 'Red Bar']  # , 'Hold Bar']#Green bar', 'Red Bar', 'Hold Bar'
        self.names_output = ['isNextBarUp']
        self.size_input = len(self.names_input)
        self.size_output = len(self.names_output2)
        self.x_train = None
        self.x_test = None
        self.y_train = None
        self.y_test = None
        self.seed = 7
        np.random.seed(self.seed)

    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def execute(self,
                df_all,
                train_data_indices,
                test_data_indices,
                iteration_id,
                model_type=MlModel.MLP,
                epochs=5000,
                size_hidden=15,
                batch_size=128,
                loss='categorical_crossentropy',
                lr=0.00001,
                rho=0.9,
                epsilon=None,
                decay=0.0,
                kernel_init='glorot_uniform',
                dropout=0.2,
                verbose=0
                , names_output2 = ['Green bar', 'Red Bar']# # , 'Hold Bar']#Green bar', 'Red Bar', 'Hold Bar'
                #, activation='softmax'#softmax'
                ):
        self.names_output2 = names_output2
        self.size_output = len(self.names_output2)
        # print('\n======================================')
        # print('Plotting features')
        # print('======================================')
        # self._plot_features(df_all, iteration_id)

        print('\n======================================')
        print(f'#{iteration_id}Splitting the data to train & test data')
        print('======================================')
        self._data_prepare_(df_all, train_data_indices, test_data_indices)

        print('\n======================================')
        print(f'#{iteration_id}Labeling the data')
        print('======================================')
        self._label_prepare(df_all, train_data_indices, test_data_indices)

        print('\n======================================')
        print(f'#{iteration_id}Normalizing the data')
        print('======================================')
        self._data_normalize()

        print('\n======================================')
        print(f'#{iteration_id}Transform data. Convert class vectors to binary class matrices (for ex. convert digit 7 to bit array['
              '0. 0. 0. 0. 0. 0. 0. 1. 0. 0.]')
        print('======================================')
        self._label_transform()

        print('\n======================================')
        print(f'#{iteration_id}Creating  model')
        print('======================================')
        model = MlModelFactory().create(model_type=model_type, size_hidden=size_hidden, size_input=self.size_input,
                                        size_output=self.size_output, dropout=dropout, kernel_init=kernel_init)
        model.compile(loss=loss, lr=lr, rho=rho, epsilon=epsilon, decay=decay)


        print('\n======================================')
        print(f'#{iteration_id}Train model for {epochs} epochs...')
        print('======================================')
        model.fit(x_train=self.x_train, y_train=self.y_train, x_test=self.x_test, y_test=self.y_test, epochs=epochs,
                  batch_size=batch_size, verbose=verbose)

        print('\n======================================')
        print(f'#{iteration_id}Predict unseen data with 2 probabilities for 2 classes(choose the highest)')
        print('======================================')
        model.predict(x_train=self.x_train, y_train=self.y_train, x_test=self.x_test, y_test=self.y_test, names_output=['dn','up'], iteration_id=iteration_id)


        print('\n======================================')
        print(f'#{iteration_id}Evaluate model with unseen data. pls validate that test accuracy =~ train accuracy and near 1.0')
        print('======================================')
        params = f'_hid{size_hidden}_RMS{lr}_epc{epochs}_batch{batch_size}_dropout{dropout}_sym{self.symbol}_inp{self.size_input}_out{self.size_output}_{model_type}'
        model.plot_evaluation(size_input=self.size_input, size_output=self.size_output, iteration_id=iteration_id,
                              title=params)
        scores = model.evaluate(x_test=self.x_test, y_test=self.y_test)




        # print('\n======================================')
        # print('Plotting histograms')
        # print('======================================')
        # self._plot_features_hstg(df_all, iteration_id)

        return scores, model, params

    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def _plot_features(self, df_all, iteration_id):
        plot_selected(df_all, title=f'{iteration_id}TA-price of {self.symbol} vs time', columns=['Close', 'sma200'],
                      shouldNormalize=False, symbol=self.symbol)
        plot_selected(df_all.tail(500), title=f'{iteration_id}TA-sma 1,10,20,50,200 of {self.symbol} vs time',
                      columns=['Close', 'sma10', 'sma20', 'sma50', 'sma200', 'sma400', 'bb_hi10', 'bb_lo10', 'bb_hi20',
                               'bb_lo20', 'bb_hi50', 'bb_lo200', 'bb_lo50', 'bb_hi200'], shouldNormalize=False,
                      symbol=self.symbol)
        plot_selected(df_all.tail(500), title=f'{iteration_id}TA-range sma,bband of {self.symbol} vs time',
                      columns=['range_sma', 'log_sma20', 'log_sma50', 'log_sma200', 'log_sma400', 'rel_bol_hi10',
                               'rel_bol_hi20', 'rel_bol_hi200', 'rel_bol_hi50'], shouldNormalize=False,
                      symbol=self.symbol)
        plot_selected(df_all.tail(500), title=f'{iteration_id}TA-rsi,stoc of {self.symbol} vs time',
                      columns=['rsi10', 'rsi20', 'rsi50', 'rsi5', 'stoc10', 'stoc20', 'stoc50', 'stoc200'],
                      shouldNormalize=False, symbol=self.symbol)

    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def _data_prepare_(self, df_all, train_data_indices, test_data_indices):
        self.x_train = df_all[self.names_input].values[train_data_indices]
        self.x_test = df_all[self.names_input].values[test_data_indices]

        print('train input', self.x_train.shape)
        print(self.x_train[0])
        print(self.x_train[1])

        print('test input', self.x_test.shape)
        print(self.x_test[0])
        print(self.x_test[1])

        print(self.x_train.shape[0], 'train input (samples)')
        print(self.x_test.shape[0], 'test input (samples)')

    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def _label_prepare(self, df_all, train_data_indices, test_data_indices):
        self.y_train = df_all[self.names_output].values[train_data_indices]
        self.y_test = df_all[self.names_output].values[test_data_indices]

        print('train output (labels)', self.y_train.shape)
        print(self.y_train[0])
        print(self.y_train[1])

        print('test output (labels)', self.y_test.shape)
        print(self.y_test[0])
        print(self.y_test[1])

        print(self.y_train.shape[0], 'train output (labels)')
        print(self.y_test.shape[0], 'test output (labels)')

    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def _data_clean(self):
        pass

    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def _data_normalize(self):
        self.x_train = normalize3(self.x_train, axis=1)
        self.x_test = normalize3(self.x_test, axis=1)
        # print('columns=', self.x_train.columns)
        # print ('\ndf1=\n',self.x_train.loc[:, ['Open','High', 'Low', 'Close', 'range']])
        # print ('\ndf1=\n',self.x_train.loc[:, ['sma10','sma20','sma50','sma200','range_sma']])
        print('finished normalizing \n',stats.describe(self.x_train))
        print('\ndfn0=\n',self.x_train[0])
        print('\ndfn=\n',self.x_train)
        # print(self.x_train2[0])
        # plot_image(self.x_test,'picture example')

    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def _data_rebalance(self):
        pass

    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def _label_transform(self):
        print(f'categorizing   {self.size_output} classes')
        self.y_train = to_categorical(self.y_train, num_classes=self.size_output)
        self.y_test = to_categorical(self.y_test, num_classes=self.size_output)
        print(f'y_train[0]={self.y_train[0]}, it means label={np.argmax(self.y_train[0])}')
        print(f'y_test[0]={self.y_test[0]}, it means label={np.argmax(self.y_test[0])}')

    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    @staticmethod
    def _plot_features_hstg(df_all, iteration_id):
        plot_histogram(x=df_all['range']
                       , bins=100
                       , title=f'{iteration_id}TA-diff bw open and close - Gaussian data '
                       , xlabel='range of a bar from open to close'
                       , ylabel='count')

        plot_histogram(x=df_all['range_sma']
                       , bins=100
                       , title=f'{iteration_id}TA-diff bw 2 sma - Gaussian data'
                       , xlabel='diff bw 2 sma 10,20  '
                       , ylabel='count')
