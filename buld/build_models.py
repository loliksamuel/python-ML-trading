from keras.callbacks import History
import eli5
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


from os import path, cpu_count
from eli5.sklearn import PermutationImportance
from keras.callbacks import History
from keras.layers import Dense, Dropout, LSTM
from keras.models import Sequential
from keras.optimizers import RMSprop
from keras.utils import to_categorical
from keras.wrappers.scikit_learn import KerasClassifier
# from sklearn.cross_validation import StratifiedShuffleSplit
from sklearn.dummy import DummyClassifier
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, accuracy_score
from sklearn.metrics.classification import classification_report
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.model_selection import train_test_split, cross_validate, StratifiedShuffleSplit
import xgboost as xgb
from sklearn.naive_bayes import GaussianNB
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.utils import shuffle

from buld.utils import plot_selected, plot_stat_loss_vs_accuracy, plot_conf_mtx, plot_histogram, plot_stat_loss_vs_accuracy2, plot_roc, plot_importance_svm, normalize_by_column, plot_importance_xgb, normalize3, print_is_stationary, create_target_label, reduce_mem_usage, feature_tool, reduce_mem_usage2, symbol_to_path, data_clean, format_col_date, GridSearchCVProgressBar
from data.features.features import Features
from data.features.transform import max_min_normalize, log_and_difference




class MlpTrading_old(object):
    def __init__(self) -> None:
        super().__init__()
        self.precision = 4
        np.set_printoptions(precision=self.precision)
        np.set_printoptions(suppress=True) #prevent numpy exponential #notation on print, default False
        self.x_train = None
        self.x_test = None
        self.y_train = None
        self.y_test = None
        self.seed = 7
        self.models_need1hot = ['mlp','lstm', 'ker', 'gridmlp']# 'xgb', 'gridxgb',#if model_type in self.models_need1hot:
        self.models_df       = [   'mlp2' ]#'gaus', 'svc','xgb','rf',
        self.params=''
        np.random.seed(self.seed)

    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def execute(self
                , data_type     = '^GSPC' #^GSPC GSPC2 iris random
                , model_type    ='drl'  #mlp lstm drl xgb gridxgb 'gridmlp','ker',
                #, names_input  = ['nvo']
                , names_output = ['Green bar', 'Red Bar']  # # , 'Hold Bar']#Green bar', 'Red Bar', 'Hold Bar'
                , skip_days    = 3600
                , epochs       = 500
                , size_hidden  = 15
                , batch_size   = 128
                , percent_test_split=0.33
                , loss         = 'categorical_crossentropy'
                , lr           = 0.00002  # default=0.001   best=0.00002
                , rho          = 0.9  # default=0.9     0.5 same
                , epsilon      = None
                , decay        = 0.0
                , kernel_init  = 'glorot_uniform'
                , dropout      = 0.2
                , verbose      = 0
                , activation   = 'softmax'  #sigmoid'
                , use_random_label = False
                , use_raw_data     = False
                , use_feature_tool = True


                ):
        self.symbol = data_type

        #self.names_output = names_output# , 'Hold Bar']#Green bar', 'Red Bar', 'Hold Bar'
        #self.names_input  = names_input
        self.size_output  = len(names_output)
        #self.size_input   = len(self.names_input)-1

        data_path_all = path.join('files', 'input', f'{data_type}')
        if (use_raw_data):
            print(f'Loading from disc raw data   ')
            df_x, df_y = self.data_prepare(percent_test_split, skip_days, use_random_label, data_type=data_type, use_feature_tool=use_feature_tool)
            if isinstance(df_x,  pd.DataFrame):
                df_x.to_csv( f'{data_path_all}_x_{use_feature_tool}.csv', index=False, header=True)
                df_y.to_csv( f'{data_path_all}_y_{use_feature_tool}.csv', index=False, header=True)

        else:
            print(f'Loading from disc prepared data :{data_path_all + "_x.csv"} ')
            df_x = pd.read_csv(f'{data_path_all}_x_{use_feature_tool}.csv')
            df_y = pd.read_csv(f'{data_path_all}_y_{use_feature_tool}.csv')

        if isinstance(df_y,  pd.DataFrame):
            self.names_output = df_y['target'].unique()
        else:
            self.names_output = pd.Series(df_y, name='target').unique()#df_y.unique()#list(iris.target_names)
        self.names_input  = df_x.columns.tolist()
        self.names_input = list(map(str, self.names_input))
        self.size_input   = len(self.names_input)
        self.size_output  = len(self.names_output)
        print(f'#features={self.size_input}, out={self.size_output}, names out={self.names_output }')
        print(f'df_y.describe()=\n{df_y.describe()}')
        print(f'\ndf_y[5]={df_y.shape}\n',df_y.head(5))
        print(f'\ndf_x[1]={df_x.shape}\n',df_x.head(1))
        #print('\ndf_x describe\n', df_x.describe())
        #print(f'length of {data_type}={len(df_y)}')
        #print('\ndft describe=\n', dft.loc[:,  ['target' ]].describe())
        #print(dft.tail())
        print('\n======================================')
        print('\nsplitting rows to train+test')
        print('\n======================================')
        (self.x_train, self.x_test, self.y_train, self.y_test) = self._split( df_x, df_y, percent_test_split)
        #self.y_train = self.y_train.values
        print('\n======================================')
        print('\nNormalizing the data(must be after split)')
        print('\n======================================')
        self.x_train = self._data_normalize(self.x_train)
        self.x_test  = self._data_normalize(self.x_test)

        # plt.figure()
        # plt.scatter(self.x_train[:, 0], self.x_train[:, 1], c=self.y_train)
        # n_samples = len(self.y_train)
        # plt.title(f"all {n_samples} train samples")
        # plt.show()

        print('\n======================================')
        print('\nTransform label. Convert class vectors to binary class matrices (1 hot encoder vector)')
        print('\n======================================')
        self._label_transform(model_type)

        self.params = f'hid{size_hidden}_rms{lr}_epo{epochs}_bat{batch_size}_dro{dropout}_sym{self.symbol}_inp{self.size_input}_out{self.size_output}_{model_type}'
        print(f'\nrunning with modelType {model_type}, data_type={data_type}, batch_size={batch_size}')
        if model_type == 'all':
            kernel2 = 'linear' #SVC(kernel='rbf')#{'C': 1.0, 'gamma': 0.1} with a score of 0.97
            models =  [SVC                   (random_state=5, kernel=kernel2, C=1, gamma=0.1)
                      ,MLPClassifier         (random_state=5, hidden_layer_sizes= (250,150,100,50,20,10,5,), shuffle=False, activation='relu', solver='adam', batch_size=batch_size, max_iter=epochs, learning_rate_init=lr)#50.86 %  #activation=('identity', 'logistic', 'tanh', 'relu'),  solver : {'lbfgs', 'sgd', 'adam'}, default 'adam'
                      ,GaussianNB            (var_smoothing=1000000e-9)
                      ,RandomForestClassifier(random_state=5, n_estimators=370, max_depth=580)#50.84 %
                     ]# solvers ('sgd', 'adam'), note that this determines the number of epochs
            for model in models:
                self.params = f'hid{size_hidden}_rms{lr}_epo{epochs}_bat{batch_size}_dro{dropout}_sym{self.symbol}_inp{self.size_input}_out{self.size_output}_{type(model).__name__}'
                model.fit(self.x_train, self.y_train)
                self.model_predict(model,  type(model).__name__)#
            #calc_scores(models, self.x_test, self.y_test)

        elif model_type == 'dummy':
            model = DummyClassifier(strategy= 'most_frequent')
            model.fit(self.x_train, self.y_train)
            self.model_predict(model,  'dummy')
        elif model_type == 'gaus':
            model = GaussianNB            ()
            model.fit(self.x_train, self.y_train)
            self.model_predict(model,  'gaus')
        elif model_type == 'rf':
            model = RandomForestClassifier(random_state=5, n_estimators=100, max_depth=50)#50.84 %
            model.fit(self.x_train, self.y_train.values.ravel())
            self.model_predict(model,  'rf')
        elif model_type == 'lr': #  binary class only
            score = cross_validate(LogisticRegression(),self.x_train, self.y_train, cv=5, scoring=('roc_auc','average_precision'))#test_roc_auc=0.5018094629156009 , test_average_precision=0.5233818847206579
            print (f"test_roc_auc={score['test_roc_auc'].mean()} , test_average_precision={score['test_average_precision'].mean()}")
            print (f"score={score}")
        elif model_type == 'mlp2':
            model = MLPClassifier         (random_state=5, hidden_layer_sizes=(950,))#50.86 %
            model.fit(self.x_train, self.y_train)
            self.model_predict(model,  'mlp2')
        elif model_type == 'ker':
            model = self.model_create_scikit(epochs=epochs, batch_size=batch_size, size_hidden=size_hidden, dropout=dropout, activation=activation, optimizer=RMSprop(lr=lr, rho=rho, epsilon=epsilon, decay=decay) )
        elif model_type == 'gridmlp':
            model = self.model_create_grid_mlp()
        elif model_type == 'gridsvc':# gridsvc is very slow(4 days). use it  only with fraction of data
            kernel = 'rbf'
            model = self.model_create_grid_csv(kernel)
        elif model_type == 'gridxgb':
            model = self.model_create_grid_xgb()
        elif model_type == 'xgb':
            model = self.model_create_xgb(epochs)
        elif model_type == 'svc':# poly is very slow(4 hours). linear is fast
            kernel2 = 'linear' #SVC(kernel='rbf')#{'C': 1.0, 'gamma': 0.1} with a score of 0.97
            model = SVC                   (random_state=5, kernel=kernel2, C=0.1, gamma=0.1)#gamma is only for 'rbf', 'poly' and 'sigmoid'.  poly, rbf, sigmoid linear
            model.fit(self.x_train, self.y_train)#df.iloc[:,1:].values
            self.model_predict(model,  'svc')

            if kernel2 == 'linear':
                print(f'svc weights: {model._get_coef()}')
                print(f'len={len(self.names_input)}, shape(n_targets, n_features)={model.coef_.shape}')#  features={self.names_input}, ')
                #self.names_input.remove('target')
                plot_importance_svm(model, self.names_input, top_features=int(self.size_input/2))
                #print('Intercept: ')
                #print(model.class_weight_)
        elif model_type == 'mlp':
            model   = self.model_create_mlp(size_input=self.size_input, size_output=self.size_output ,activation=activation, optimizer=RMSprop(lr=lr, rho=rho, epsilon=epsilon, decay=decay), loss=loss, init=kernel_init, size_hidden=size_hidden, dropout=dropout, lr=lr, rho=rho, epsilon=epsilon, decay=decay)
            model.summary()
            history = self.model_fitt    (model, batch_size=batch_size, epochs=epochs, verbose=verbose)
            model   = self.model_predictt(model,history, model_type)
            ok      = self.model_save    (model)
        elif model_type == 'lstm':
            model   = self._model_create_lstm(activation=activation, optimizer=RMSprop(lr=lr, rho=rho, epsilon=epsilon, decay=decay),  loss=loss, init=kernel_init, size_hidden=size_hidden, dropout=dropout, lr=lr, rho=rho, epsilon=epsilon, decay=decay)
            history = self.model_fitt    (model, batch_size=batch_size, epochs=epochs, verbose=verbose)
            model   = self.model_predictt(model,history,  model_type)
            ok      = self.model_save    (model)
        else:
            print('unsupported model. exiting')
            exit(0)


    def data_prepare(self, skip_days, use_random_label=False, data_type='iris', use_feature_tool=False):

        if (data_type == 'iris'):#iris data 3 classes
            print('\n======================================')
            print(f'Loading  iris data ')
            print('\n======================================')
            iris = load_iris()#return_X_y=True)

            #df_data = pd.DataFrame(iris.data, columns=iris.feature_names)
            df_data = pd.DataFrame( data   = np.c_[iris['data'], iris['target']]
                                    , columns= iris ['feature_names'] + ['target'])
            df_data = df_data.sample(frac=1)#shuffle cause the first 100 samples are 0
            #df_x,df_y = shuffle(X, y)
            df_y = df_data['target']  # np.random.randint(0,2,size=(shape[0], ))
            df_x = df_data.drop(columns=['target'])
            print('\ndf_x describe=\n', df_x.describe())

        elif (data_type == 'random'): #random 2 classes
            print('\n======================================')
            print(f'Loading random binary data ')
            print('\n======================================')
            random_state = np.random.RandomState(0)
            n_samples    = 200
            X            = random_state.rand(n_samples, 2)
            y            = np.ones(n_samples)
            y[X[:, 0] + 0.1 * random_state.randn(n_samples) < 0.5] = 0.0

            df_y = pd.DataFrame( data   = np.c_[y]
                                 , columns= ['target'] )
            df_x = pd.DataFrame( data   = np.c_[X]
                                 , columns= ['f1','f2']  )
            print('\ndf_x describe=\n', df_x.describe())

        elif data_type.startswith('spy'):
            if (data_type == 'spyp283'):#stationarized data
                data_path = path.join('files', 'input', '^GSPC_1998_2019_v2_vec283.csv')
                print(f'Loading from disc prepared data3 :{data_path} ')
                df_data = pd.read_csv(data_path)

                df_data.drop(columns=[  'TRIX50', 'v_obv'], axis=1, inplace=True)
                features_to_stationarize = [ 'High', 'Close', 'CloseVIX', 'Volume', 'v_nvo',  'v_ad', 'BBANDH2', 'BBANDM2', 'BBANDL2',  'BBANDH4', 'BBANDM4', 'BBANDL4', 'BBANDH8', 'BBANDM8', 'BBANDL8', 'BBANDH14', 'BBANDM14', 'BBANDL14', 'BBANDH20', 'BBANDM20', 'BBANDL20', 'BBANDH30', 'BBANDM30', 'BBANDL30', 'BBANDH50', 'BBANDM50', 'BBANDL50'  ,    'MINUS_DM30', 'PLUS_DM30', 'MINUS_DM50', 'PLUS_DM50']#,'v_obv', 'TRIX50']
                print(f'before stationarize describe=\n{df_data.loc[:,  features_to_stationarize].describe()}')
                #df_data = max_min_normalize (df_data, inplace = False, columns=features_to_stationarize)
                df_data = log_and_difference(df_data, inplace = False, columns=features_to_stationarize)
                df_data = create_target_label(df_data,2,False)
                df_data.drop(columns=[ 'High', 'range0', 'isUp', 'percentage'], axis=1, inplace=True)

            elif (data_type == 'spyp71'):
                data_path     = path.join('files', 'input', '^GSPC_1964_2019_v1_vec71.csv')
                print(f'Loading from disc prepared data2 :{data_path} ')
                df_data = pd.read_csv(data_path)
                #df_data.drop(columns=[ 'High', 'range0', 'isUp', 'percentage'], axis=1, inplace=True)

            elif (data_type == 'spy71' or data_type == 'spy283'):
                #df_data = data_load_and_transform  (self.symbol, usecols=['Date', 'Close', 'Open', 'High', 'Low', 'Adj Close', 'Volume'], skip_first_lines = skip_days, size_output=self.size_output, use_random_label=use_random_label, feature_src='ta')
                print(f'\nLoading from disc raw data using {data_type} features')
                fetures = Features(skip_first_lines=skip_days)

                #dfc = data_clean(df1)
                if data_type == 'spy71':
                    data_path     = path.join('files', 'input', '^GSPC_1950_2019_v1_vec7.csv')
                    data_path = pd.read_csv(data_path#symbol_to_path('^GSPC')#^GSPC.csv
                                      # , index_col='Date'
                                      # , parse_dates=True
                                      , usecols=['Date', 'Close', 'Open', 'High', 'Low', 'Adj Close', 'Volume']
                                      , na_values=['nan'])
                    df_data  = fetures.add_features(data_path, 71)
                    #features_to_stationarize = [ 'High', 'Close']
                    #print(f'before stationarize describe=\n{df_data.loc[:,  features_to_stationarize].describe()}')
                    #df_data = log_and_difference(df_data, inplace = False, columns=features_to_stationarize)
                    ###df_data = data_transform(dfc, skip_days ,self.size_output, use_random_label)

                    #     Date            ,High          , Close            ,  Volume                            , CloseVIX,  SKEW,     STOCH_SLOWK,STOCH_SLOWD,STOCHF_FASTK,STOCHF_FASTD,STOCHRSI_FASTK,STOCHRSI_FASTD,MACD,MACDSIGNAL,MACDHIST,MACDEXT,MACDEXTSIGNAL,MACDEXTHIST,PPO,APO,ULTOSC,BOP,CMO2,MOM2,RSI2,TRIX2,ROC2,ROCP2,ROCR2,ROCR1002,MFI2,ADX2,ADXR2,CCI2,DX2,WILLR2,MINUS_DI2,PLUS_DI2,MINUS_DM2,PLUS_DM2,AROONOSC2,AROONDN2,AROONUP2,MACDFIX2,MACDSIGNALFIX2,MACDHISTFIX2,BBANDH2,BBANDM2,BBANDL2,CMO4,MOM4,RSI4,TRIX4,ROC4,ROCP4,ROCR4,ROCR1004,MFI4,ADX4,ADXR4,CCI4,DX4,WILLR4,MINUS_DI4,PLUS_DI4,MINUS_DM4,PLUS_DM4,AROONOSC4,AROONDN4,AROONUP4,MACDFIX4,MACDSIGNALFIX4,MACDHISTFIX4,BBANDH4,BBANDM4,BBANDL4,CMO8,MOM8,RSI8,TRIX8,ROC8,ROCP8,ROCR8,ROCR1008,MFI8,ADX8,ADXR8,CCI8,DX8,WILLR8,MINUS_DI8,PLUS_DI8,MINUS_DM8,PLUS_DM8,AROONOSC8,AROONDN8,AROONUP8,MACDFIX8,MACDSIGNALFIX8,MACDHISTFIX8,BBANDH8,BBANDM8,BBANDL8,CMO14,MOM14,RSI14,TRIX14,ROC14,ROCP14,ROCR14,ROCR10014,MFI14,ADX14,ADXR14,CCI14,DX14,WILLR14,MINUS_DI14,PLUS_DI14,MINUS_DM14,PLUS_DM14,AROONOSC14,AROONDN14,AROONUP14,MACDFIX14,MACDSIGNALFIX14,MACDHISTFIX14,BBANDH14,BBANDM14,BBANDL14,CMO20,MOM20,RSI20,TRIX20,ROC20,ROCP20,ROCR20,ROCR10020,MFI20,ADX20,ADXR20,CCI20,DX20,WILLR20,MINUS_DI20,PLUS_DI20,MINUS_DM20,PLUS_DM20,AROONOSC20,AROONDN20,AROONUP20,MACDFIX20,MACDSIGNALFIX20,MACDHISTFIX20,BBANDH20,BBANDM20,BBANDL20,CMO30,MOM30,RSI30,TRIX30,ROC30,ROCP30,ROCR30,ROCR10030,MFI30,ADX30,ADXR30,CCI30,DX30,WILLR30,MINUS_DI30,PLUS_DI30,MINUS_DM30,PLUS_DM30,AROONOSC30,AROONDN30,AROONUP30,MACDFIX30,MACDSIGNALFIX30,MACDHISTFIX30,BBANDH30,BBANDM30,BBANDL30,CMO50,MOM50,RSI50,TRIX50,ROC50,ROCP50,ROCR50,ROCR10050,MFI50,ADX50,ADXR50,CCI50,DX50,WILLR50,MINUS_DI50,PLUS_DI50,MINUS_DM50,PLUS_DM50,AROONOSC50,AROONDN50,AROONUP50,MACDFIX50,MACDSIGNALFIX50,MACDHISTFIX50,BBANDH50,BBANDM50,BBANDL50,HT_DCPERIOD,HT_DCPHASE,INPHASE,QUADRATURE,SINE,LEADSINE,HT_TRENDMODE,ATR,NATR,TRANGE,CDL3INSIDE,CDL3LINESTRIKE,CDL3OUTSIDE,CDL3WHITESOLDIERS,CDLADVANCEBLOCK,CDLBELTHOLD,CDLCLOSINGMARUBOZU,CDLDARKCLOUDCOVER,CDLDOJI,CDLDOJISTAR,CDLDRAGONFLYDOJI,CDLENGULFING,CDLEVENINGDOJISTAR,CDLEVENINGSTAR,CDLGAPSIDESIDEWHITE,CDLGRAVESTONEDOJI,CDLHAMMER,CDLHANGINGMAN,CDLHARAMI,CDLHARAMICROSS,CDLHIGHWAVE,CDLHIKKAKE,CDLHIKKAKEMOD,CDLHOMINGPIGEON,CDLIDENTICAL3CROWS,CDLINNECK,CDLINVERTEDHAMMER,CDLLADDERBOTTOM,CDLLONGLEGGEDDOJI,CDLLONGLINE,CDLMARUBOZU,CDLMATCHINGLOW,CDLMORNINGDOJISTAR,CDLMORNINGSTAR,CDLONNECK,CDLPIERCING,CDLRICKSHAWMAN,CDLSEPARATINGLINES,CDLSHOOTINGSTAR,CDLSHORTLINE,CDLSPINNINGTOP,CDLSTALLEDPATTERN,CDLSTICKSANDWICH,CDLTAKURI,CDLTASUKIGAP,CDLTHRUSTING,CDLUNIQUE3RIVER,CDLXSIDEGAP3METHODS,v_nvo,v_obv,v_ad,v_ado,dt_day_sin,dt_wk_sin,dt_month_sin,dt_day_cos,dt_wk_cos,dt_month_cos,R_H0_L0,R_C0_C1,R_C0_C2,R_H0_L0VX,R_C0_C1VX,R_C0_C2VX,range0,range1,range2
                    #148 ,902275200       ,1084.8        , 1081.4           , 851600000                          , 29.83   , 121.17,
                    #5431,1566259200      ,2923.6        , 2900.5           ,3066300000                          , 17.5    ,114.78 , 69.34,48.55806891586209,71.09679316492492,69.34

                    #    Date    , Open  , High  , Low  , Close  , Adj Close,  Volume,    OpenVIX,HighVIX,LowVIX,  CloseVIX,  SKEW
                    #1997-12-31,  970.8 , 975.0 , 967.4,  970.4  ,  970.429 , 467280000  , 24.2  ,24.52  ,23.59 ,  24.01   , 119.62
                    #2019-08-20,  2919  ,2923.6 ,2899.6,  2900.5 ,  2900.5  ,3066300000  , 16.7  ,17.70  ,16.45 ,  17.5    , 114.78
                elif data_type == 'spy283': #^GSPC_1998_2019_v2_vec12
                    data_path = path.join('files', 'input', '^GSPC_1998_2019_v2_vec12.csv')
                    data_path = pd.read_csv(data_path)
                    df_data   = fetures.add_features(data_path, 283)
                    df_data   = format_col_date(df_data)
                    #df_data  = sort_by_date      (df_data     )
                    df_data.drop(columns=[  'TRIX50', 'v_obv'], axis=1, inplace=True)
                    features_to_stationarize = [ 'High', 'Close', 'CloseVIX', 'Volume', 'v_nvo',  'v_ad', 'BBANDH2', 'BBANDM2', 'BBANDL2',  'BBANDH4', 'BBANDM4', 'BBANDL4', 'BBANDH8', 'BBANDM8', 'BBANDL8', 'BBANDH14', 'BBANDM14', 'BBANDL14', 'BBANDH20', 'BBANDM20', 'BBANDL20', 'BBANDH30', 'BBANDM30', 'BBANDL30', 'BBANDH50', 'BBANDM50', 'BBANDL50'  ,    'MINUS_DM30', 'PLUS_DM30', 'MINUS_DM50', 'PLUS_DM50']#,'v_obv', 'TRIX50']
                    print(f'before stationarize describe=\n{df_data.loc[:,  features_to_stationarize].describe()}')
                    #df_data = max_min_normalize (df_data, inplace = False, columns=features_to_stationarize)
                    df_data = log_and_difference(df_data, inplace = False, columns=features_to_stationarize)
                    #df_data.drop(columns=[ 'isUp'], axis=1, inplace=True)
                    #df.drop(columns=['Open', 'Low', 'Adj Close', 'OpenVIX', 'HighVIX', 'LowVIX']
                df_data = create_target_label(df_data, self.size_output, use_random_label)
                df_data.drop(columns=[ 'High', 'range0', 'isUp', 'percentage'], axis=1, inplace=True)

            df_data.drop(columns=['Date'], axis=1, inplace=True)
            df_y = df_data['target']  # np.random.randint(0,2,size=(shape[0], ))
            df_x = df_data.drop(columns=['target'])
            #df_x = data_clean(df_x)
        else:
            raise ValueError(  'Error: unknown data type')

        # self._plot_features(dft)
        #  https://www.oipapio.com/question-3322022
        # df_all = df_all.values.reshape(samples,timestamps,features)
        df_x = df_x.round(self.precision)
        df_x.style.format("{:.4f}")
        #df_x, df_y = self._data_rebalance(df_x, df_y)
        #df_x = reduce_mem_usage(df_x)
        self.names_input  = df_x.columns.tolist()
        self.size_input   = len(self.names_input)
        #self.size_output  = len(self.names_output)
        print(f'#features={self.size_input}, out={self.size_output}')

        if use_feature_tool == True:
            df_x = feature_tool(df_x)


        return df_x, df_y

    def model_create_grid_mlp(self):#34 hours
        print("use_grid_search")
        inits       = ['glorot_uniform']#, 'zero', 'uniform', 'normal', 'lecun_uniform',  'glorot_uniform',  'he_uniform', 'he_normal']#all same except he_normal worse
        losses      = ['categorical_crossentropy']#, 'categorical_crossentropy']#['mse', 'mae']  #better=binary_crossentropy
        activations = [ 'softmax']#'sigmoid']#, 'softplus', 'softsign', 'sigmoid',  'tanh', 'hard_sigmoid', 'linear', 'relu']#best 'softmax', 'softplus', 'softsign'
        optimizers  = ['SGD']#RMSprop']#, 'SGD']#, 'Adagrad', 'Adadelta', 'Adam', 'Adamax', 'Nadam'] # same for all
        epochs      = [8]#[300, 800]  # , 100, 150] # default epochs=1,  better=100
        batch_sizes = [128]#[12,128]#],150,200]  # , 10, 20]   #  default = none best=32
        size_hiddens= [6]#[ 200, 600]  # 5, 10, 20] best = 100 0.524993 Best score: 0.525712 using params {'batch_size': 128, 'dropout': 0.2, 'epochs': 100, 'loss': 'binary_crossentropy', 'size_hidden': 100}
        lrs     =      [0.001]#[0.01, 0.001, 0.00001]#,0.03, 0.05, 0.07]#,0.001,0.0001,1,0.1,0.00001]#best 0.01 0.001 0.0001
        dropouts =     [0.2]#, 0.2, 0.3, 0.4]  # , 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        weights =      [1, 2]  # , 3, 4, 5]
        rhos    =      [0.01, 0.1, 0.2, 0.6]#all same
        param_grid = dict( activation  = activations,
                            init=inits,
                            optimizer=optimizers,
                            epochs=epochs,
                            batch_size=batch_sizes,
                            loss= losses,
                            size_hidden = size_hiddens,
                            lr= lrs
                            #dropout=dropouts,
                            #weight_constraint=weights,
                            #rho = rhos
                            )
        sk_params = {'size_input': self.size_input ,  'size_output':self.size_output}
        model = KerasClassifier(build_fn=self.model_create_mlp, **sk_params)
        #perm = PermutationImportance(model, random_state=1).fit(self.x_test, self.y_test)
        # weights = eli5.formatters.as_dataframe.explain_weights_df(perm, feature_names=self.names_input)
        # print('\nweights=',weights)
        # dfs = [self.x_train, self.x_test]
        # x_all = pd.concat(dfs)
        # dfs = [self.y_train, self.y_test]
        # y_all = pd.concat(dfs)
        # X = np.concatenate((self.x_train, self.x_test), axis=0)
        # Y = np.concatenate((self.y_train, self.y_test), axis=0)
        tscv = TimeSeriesSplit(n_splits=2)
        cv=tscv.split(self.x_train)
        grid = GridSearchCV(estimator=model, param_grid=param_grid, cv=cv#number of folds iמ StratifiedKFold    or use cv=tscv.split(X)) #X : array-like, shape (n_samples, n_features) Training data
                            , verbose=2
                            , scoring=None#If None, the estimator's score method is used.
                            )
        #grid = GridSearchCVProgressBar(estimator=model, param_grid=param_grid,  scoring='accuracy', cv=cv_(), n_jobs=cpu_count()-1)
        grid_result = grid.fit(self.x_train, self.y_train, verbose=2)
        # summarize results
        print("The best parameters are %s with a score of %0.2f  "  % (grid.best_params_, grid.best_score_))
        #print(f'scorer={grid.scorer_}')
        print("the best parameters are %s with a score of %0.2f " % (grid_result.best_params_, grid_result.best_score_))
        means  = grid_result.cv_results_['mean_test_score']
        stds   = grid_result.cv_results_['std_test_score' ]
        params = grid_result.cv_results_['params'         ]
        for mean, stdev, param in zip(means, stds, params):
            print("%f (%f) with params: %r" % (mean, stdev, param))
        # self.model_predict(grid, 'gridmlp')
        # y_true, y_pred = self.y_test, grid.predict(self.x_test)
        # print(classification_report(y_true, y_pred))
        return model

    def model_create_grid_xgb(self):
        param_grid = {'max_depth'    : [14,19,24],#The best parameters are {'learning_rate': 0.001, 'max_depth': 19, 'n_estimators': 420} with a score of 0.52
                      'n_estimators' : [320,370,420],
                      'learning_rate': [0.001]
                      }
        model = xgb.XGBClassifier()
        cv          = StratifiedShuffleSplit(n_splits=5, test_size=0.2, random_state=42)
        grid      = GridSearchCV(estimator=model, param_grid=param_grid,  scoring='accuracy', verbose=1)#, cv=cv)

        grid_result = grid.fit(self.x_train, self.y_train, verbose=1)
        print("The best parameters are %s with a score of %0.2f"  % (grid.best_params_, grid.best_score_))

    def model_create_grid_csv(self, kernel):
        C_range     = np.logspace(-2, 10, 13)
        gamma_range = np.logspace(-9, 3, 13)
        param_grid  = dict(gamma=gamma_range, C=C_range)

        model  = SVC(kernel=kernel)
        cv          = StratifiedShuffleSplit(n_splits=3, test_size=0.2, random_state=42)
        grid       = GridSearchCV(estimator=model, param_grid=param_grid, scoring='accuracy', verbose=1, cv=cv)
        grid_result = grid.fit(self.x_train, self.y_train)
        #The best parameters are {'C': 10000000.0, 'gamma': 1e-07} with a score of 0.98
        #The best parameters are {'C': 1.0, 'gamma': 0.1} with a score of 0.97
        print("The best parameters are %s with a score of %0.2f"   % (grid.best_params_, grid.best_score_))



    def model_create_xgb(self, epochs):
        # https://www.datacamp.com/community/tutorials/xgboost-in-python
        #model = xgb.XGBRegressor(objective='reg:linear', colsample_bytree=0.3, learning_rate=0.1, max_depth=5, alpha=10,  n_estimators=10)

        print(self.y_train.shape)
        model = xgb.XGBClassifier(max_depth         =29,#20=52.19 19=18 53.02% , 17=51.75
                                  gamma             =0, #  misunderstood parameter, it acts as a regularization (0,1,5)
                                  learning_rate     =0.001,
                                  n_estimators      =epochs,# # of sub trees
                                  subsample         =1,#  % of rows used for each tree (0.5-1)
                                  colsample_bytree  =1, #  % of cols used for each tree.(0.5-1)
                                  colsample_bylevel =1, reg_alpha=0, reg_lambda=0,max_delta_step=0,
                                  min_child_weight  =1, silent=True,
                                  scale_pos_weight  =1, seed=1, missing=None
                                  , objective='binary:logistic')# multi:softprob   or    binary:logistic)

        eval_set = [(self.x_train, self.y_train), (self.x_test, self.y_test)]
        METRIC1 = "error" # merror or error
        METRIC2 = "logloss" # mlogloss or logloss

        model.fit(self.x_train
                  , self.y_train
                  , eval_metric=[METRIC1, METRIC2]
                  , verbose=True
                  , eval_set=eval_set)
        self.model_predict(model,  model_type='xgb')

        score = model.score(self.x_test, self.y_test)
        print(f'error= {score} (#(wrong cases)/#(all cases)')

        results = model.evals_result()
        epochs = len(results['validation_0'][METRIC1])
        x_axis = range(0, epochs)

        # plot log loss
        fig, ax = plt.subplots()
        ax.plot(x_axis, results['validation_0'][METRIC2], label='Train')
        ax.plot(x_axis, results['validation_1'][METRIC2], label='Test')
        ax.legend()
        plt.ylabel('mLog Loss')
        plt.title('XGBoost Log Loss')
        plt.savefig(f'files/output/{self.params}_logloss.png')

        # plot classification error
        fig, ax = plt.subplots()
        ax.plot(x_axis, results['validation_0'][METRIC1], label='Train')
        ax.plot(x_axis, results['validation_1'][METRIC1], label='Test')
        ax.legend()
        plt.ylabel('Classification Error')
        plt.title('XGBoost Classification Error')
        plt.savefig(f'files/output/{self.params}_error.png')

        plot_importance_xgb(model)
        return model





    def model_create_scikit(self, epochs=100, batch_size=128, size_hidden=15, dropout=0.2, optimizer='rmsprop', activation='sigmoid',   model_type='ker'):
        sk_params = { 'size_input' : self.size_input
                    , 'size_output': self.size_output
                    , 'size_hidden': size_hidden
                    , 'dropout'    : dropout
                    , 'optimizer'  : optimizer
                    , 'activation' : activation}
        model = KerasClassifier(build_fn=self.model_create_mlp, **sk_params)
        history = model.fit(self.x_train, self.y_train, sample_weight=None, batch_size=batch_size, epochs=epochs,  verbose=1)  # validation_data=(self.x_test, self.y_test) kwargs=kwargs)

        self.model_weights(model, self.x_test, self.y_test, self.names_input)
        plot_stat_loss_vs_accuracy2(history.history)
        plt.savefig(f'files/output/{self.params}_Accuracy.png')
        score = model.score(self.x_test, self.y_test)
        print(f'accuracy= {score} ')
        self.model_predict(model,  model_type=model_type)
        return model


    def model_fitt(self, model, batch_size=128, epochs=200, verbose=2)->History:
        print('\n======================================')
        print(f"\nTrain model for {epochs} epochs...")
        print('\n======================================')
        history = self.model_fit(model, epochs, batch_size, verbose)
        return history

    def model_predictt(self, model, history  ,  model_type='xxx'):
        print('\n======================================')
        print('\nPrinting history')
        print('\n======================================')
        # model Loss, accuracy over time_hid003_RMS0.00001_epc5000_batch128_+1hid
        # model Loss, accuracy over time_hid003_RMS0.00001_epc5000_batch128_+1hid
        #params = f'_hid{size_hidden}_RMS{lr}_epc{epochs}_batch{batch_size}_dropout{dropout}_sym{self.symbol}_inp{self.size_input}_out{self.size_output}_{modelType}'
        self.plot_evaluation( history )
        print('\n======================================')
        print('\nEvaluate the model with unseen data. pls validate that test accuracy =~ train accuracy and near 1.0')
        print('\n======================================')
        self.model_evaluate(model,self.x_test, self.y_test)
        print('\n======================================')
        print(f'\nPredict unseen data with {self.size_output} probabilities, for classes {self.names_output} (choose the highest)')
        print('\n======================================')
        self.model_predict(model, model_type=model_type)

        return model







    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def _plot_features(self, df_all):
        plot_selected(df_all, title=f'TA-price of {self.symbol} vs time', columns=['Close', 'sma200'],
                      shouldNormalize=False, symbol=self.symbol)
        plot_selected(df_all.tail(500), title=f'TA-sma 1,10,20,50,200 of {self.symbol} vs time',
                      columns=['Close', 'sma10', 'sma20', 'sma50', 'sma200', 'sma400', 'bb_hi10', 'bb_lo10', 'bb_hi20',
                               'bb_lo20', 'bb_hi50', 'bb_lo200', 'bb_lo50', 'bb_hi200'], shouldNormalize=False,
                      symbol=self.symbol)
        plot_selected(df_all.tail(500), title=f'TA-range sma,bband of {self.symbol} vs time',
                      columns=['range_sma', 'log_sma20', 'log_sma50', 'log_sma200', 'log_sma400', 'rel_bol_hi10',
                               'rel_bol_hi20', 'rel_bol_hi200', 'rel_bol_hi50'], shouldNormalize=False,
                      symbol=self.symbol)
        plot_selected(df_all.tail(500), title=f'TA-rsi,stoc of {self.symbol} vs time',
                      columns=['rsi10', 'rsi20', 'rsi50', 'rsi5', 'stoc10', 'stoc20', 'stoc50', 'stoc200'],
                      shouldNormalize=False, symbol=self.symbol)

        plt.figure(figsize = (9, 5))
        df_all['rsi5'].plot(kind ="hist")
        plt.savefig('files/output/TA-rsi5.png')

        corrmat = df_all.corr()
        f, ax = plt.subplots(figsize =(9, 8))
        sns.heatmap(corrmat, ax = ax, cmap ="YlGnBu", linewidths = 0.1)

        #corrmat = df_all.corr()
        cg = sns.clustermap(corrmat, cmap ="YlGnBu", linewidths = 0.1);
        plt.setp(cg.ax_heatmap.yaxis.get_majorticklabels(), rotation = 0)
        plt.savefig('files/output/TA-corr.png')

        #np.plotScatterMatrix(df_all,10,20)

        # sns.set(style="ticks")
        # sns.pairplot(df_all)






    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def _data_split_x(self, df, percent_test_split):
        #df_data = df_data.drop(columns=['target'])
        (self.x_train, self.x_test) = train_test_split(df, test_size=percent_test_split,  shuffle=False)  # shuffle=False in timeseries
        # # tscv = TimeSeriesSplit(n_splits=5)


    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def _split(self, df_x, df_y, percent_test_split):

        (self.x_train, self.x_test) = train_test_split(df_x, test_size=percent_test_split, shuffle=False)
        (self.y_train, self.y_test) = train_test_split(df_y, test_size=percent_test_split, shuffle=False)
        return (self.x_train, self.x_test, self.y_train, self.y_test)
        # print(df.tail())
        # print('\nlabel describe\n', df.describe())
        # # (self.x_train, self.y_train)  = train_test_split(df.as_matrix(), test_size=0.33, shuffle=False)
        #
        # print('\ntrain labels', self.y_train.shape)
        # print(self.y_train[0])
        # print(self.y_train[1])
        #
        # print('\ntest labels', self.y_test.shape)
        # print(self.y_test[0])
        # print(self.y_test[1])

    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def _data_clean(self, df):
        print('\n======================================')
        print('\nCleaning the data')
        print('\n======================================')
        return df

    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def _data_normalize(self, df):

        #df1 = normalize_by_column(df)
        #df = log_and_difference(df, inplace = False)
        df =  max_min_normalize(df, inplace = False)
        #print_is_stationary(df)

        #df3 = normalize3(df, axis=1)
        # self.x_train = normalize3(self.x_train, axis=1)
        # self.x_test  = normalize3(self.x_test , axis=1)
        # print('columns=', self.x_train.columns)
        # print ('\ndf1=\n',self.x_train.loc[:, ['Open','High', 'Low', 'Close', 'range0']])
        # print ('\ndf1=\n',self.x_train.loc[:, ['sma10','sma20','sma50','sma200','range_sma']])
        #print('finished normalizing \n',stats.describe(df))
        #print('\ndfn0=\n',df[0])
        print('\nx_norm[0:2]=\n',df[0:2])
        return df

        '''
finished normalizing  DescribeResult
(nobs=9315, 
            'nvo', 'mom5', 'mom10', 'mom20', 'mom50',  'range_sma', 'log_sma20', 'log_sma50', 'log_sma200', 'log_sma400', 'rel_bol_lo10', 'rel_bol_hi20', 'rel_bol_lo20', 'rel_bol_hi50', 'rel_bol_lo50'  'rel_bol_hi200',  'rel_bol_lo200', 'rsi10', 'rsi20', 'rsi50', 'rsi5', 'stoc10', 'stoc20', 'stoc50', 'stoc200'
min=       [ 0.63, -0.21,  -0.21,  -0.18   ,  -0.18  , -0.  , -0.  , -0.  , -0.  ,-0.  , -0.  , -0.  , -0.  , -0.  , -0.  , -0.  , -0.  ,  0.  ,0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ]), 
max=       [ 1.  , -0.  , -0.  , -0.  , -0.          ,  0.  ,  0.  ,  0.  ,  0.  ,0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.27,0.26,  0.24,  0.26,  0.26,  0.29,  0.29,  0.3 ])), 
mean=      [ 0.99, -0.02, -0.02, -0.02, -0.02,         -0.  ,  0.  ,  0.  ,  0.  ,0.  ,  0.  , -0.  ,  0.  , -0.  ,  0.  , -0.  ,  0.  ,  0.02,0.02,  0.02,  0.02,  0.02,  0.02,  0.02,  0.03]), 
var =      [ 0.  , 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.,0., 0., 0., 0., 0., 0., 0., 0.]), 
      
      normalize0*100
 min([ 0.6276, -0.2057, -0.209 , -0.1825, -0.1757, -0.004 , -0.005 ,-0.0077, -0.0164, -0.0114, -0.0025, -0.0147, -0.0027, -0.026 ,-0.0041, -0.0437, -0.0075,  0.0002,  0.0004,  0.0009, 0.0001,0.    ,  0.    ,  0.    ,  0.    ]), 
 max([ 1.    , -0.    , -0.    , -0.    , -0.    ,  0.0039,  0.005 ,    0.0096,  0.0188,  0.0214,  0.0097,  0.0013,  0.021 ,  0.0024, 0.0356,  0.012 ,  0.0597,  0.2654,  0.2613,  0.2395,  0.259 , 0.2555,  0.2868,  0.2934,  0.3028])), 
 mean([ 0.9934, -0.021 , -0.0204, -0.0196, -0.0186, -0.    ,  0.    ,0.0001,  0.0005,  0.0009,  0.0005, -0.0009,  0.0009, -0.0015,0.0017, -0.003 ,  0.0042,  0.0223,  0.0223,  0.0223,  0.0222,0.0225,  0.0233,  0.0243,  0.0268]), 
 var([0.0002, 0.0006, 0.0006, 0.0006, 0.0006, 0.    , 0.    , 0.    , 0.    , 0.    , 0.    , 0.    , 0.    , 0.    , 0.    , 0.    , 0.    , 0.0005, 0.0005, 0.0004, 0.0006, 0.0006, 0.0006, 0.0006, 0.0008]), 
       
       normalize3
 min([ -1.583 ,  -1.8729,  -1.9074,  -1.9675,  -2.1006, -20.2001, -11.8513,  -7.7558,  -4.4229,  -3.6384, -21.8447,  -5.0579,-16.8103,  -7.6295, -10.3472,  -7.6404,  -7.0404,  -3.5015, -2.4874,  -2.9664,  -3.5163,  -1.9537,  -1.9074,  -1.9675,-2.1006,  -2.2853]), 
 max([7.0308, 1.5706, 1.5023, 1.4322, 1.3643, 5.3087, 4.172 , 2.9205,2.0347, 1.8618, 2.0737, 8.4973, 1.7524, 6.2461, 1.5518, 4.7587,1.6522, 2.7927, 2.1145, 2.4315, 2.7735, 1.688 , 1.5023, 1.4322,1.3643, 1.1531])), 
 mean([-0.,  0.,  0.,  0., -0.,  0.,  0.,  0., -0.,  0., -0.,  0., -0.,-0.,  0.,  0., -0.,  0.,  0.,  0., -0., -0.,  0.,  0., -0., -0.]), 
 var([1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001,1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001, 1.0001])
 
        '''
        # print(self.x_train2[0])
        # plot_image(self.x_test,'picture example')

    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def _data_rebalance(self, df_x, df_y):
        #use over sampling or under sampling cause 53% green bars
        #df_x, df_y = obj.sample(df_x, df_y )
        return df_x, df_y

        # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def _label_transform(self, modelType):
        print(f'categorizing   {self.size_output} classes')
        #print('y_train[0:10]=',self.y_train[0:10])
        #print('y_test[0:10]=',self.y_test[0:10])
        # self.y_train = shift(self.y_train,1)
        # self.y_test  = shift(self.y_test,1)
        #self.y_train_bak = self.y_train

        if modelType in self.models_need1hot :
            self.y_train = to_categorical(self.y_train, num_classes=self.size_output)
            self.y_test  = to_categorical(self.y_test , num_classes=self.size_output)
            print(f'y_train[0]={self.y_train[0]}, it is in index {np.argmax(self.y_train[0])}')
            print(f'y_test [0]={self.y_test[0]}, it is in index {np.argmax(self.y_test[0])}')

    # |--------------------------------------------------------|
    # |                                            |
    # |--------------------------------------------------------|
    def model_create_mlp(self, size_input=28 ,  size_output=2 ,  activation='relu', optimizer='rmsprop', loss='categorical_crossentropy', init='glorot_uniform', size_hidden=15, dropout=0.2, lr=0.001, rho=0.9, epsilon=None, decay=0.0):

        model = Sequential()  # stack of layers

        model.add(Dense  (units=size_hidden, activation=activation, input_shape=(size_input,), kernel_initializer=init))
        model.add(Dropout(dropout))  # for generalization

        model.add(Dense  (units=size_hidden, activation=activation))
        model.add(Dropout(dropout))#for generalization.

        model.add(Dense  (units=size_hidden, activation=activation))
        model.add(Dropout(dropout))  # regularization technic by removing some nodes
        print(f'hid={size_hidden}, lr={lr}, ctv={activation}, ptm={optimizer}, batch_sizes=?, loss={loss}, rho={rho}, eps={epsilon}, dec={decay}, init={init}, in={self.size_input} out={self.size_output} ')
        model.add(Dense  (units=size_output, activation=activation))
        #model.summary()

        self._model_compile(model, optimizer='SGD' # rmsprop SGD RMSprop(lr=lr, rho=rho, epsilon=epsilon, decay=decay)
                                 ,  loss=loss, lr=lr, rho=rho, epsilon=epsilon, decay=decay)

        return model



    def _model_create_lstm(self, activation='relu', optimizer='rmsprop', loss='categorical_crossentropy', init='glorot_uniform', size_hidden=50, dropout=0.2,  lr=0.001, rho=0.9, epsilon=None, decay=0.0):
        #input_shape = (input_length, input_dim)
        #input_shape=(self.size_input,)   equals to    input_dim = self.size_input
        #X_train = np.reshape(X_train, (X_train.shape[0], 1, X_train.shape[1]))
        #X_test = np.reshape(X_test, (X_test.shape[0], 1, X_test.shape[1]))

        # X_train = []
        # Y_train = []
        #
        # for i in range(60, 2035):
        #     X_train.append(self.x_train[i-60:i, 0])
        #     Y_train.append(self.x_train[i, 0])
        # X_train, Y_train = np.array(X_train), np.array(Y_train)
        #
        # X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))
        lookback = 2# Error when checking input: expected lstm_1_input to have shape (2, 39) but got array with shape (1, 39)
        lookback = 1

        print('b4 adding 1 dimension for lstm')
        # self.x_train = format_to_lstm(self.x_train, lookback)
        # self.x_test  = format_to_lstm(self.x_test, lookback)
        self.x_train = np.reshape(self.x_train, (self.x_train.shape[0], lookback, self.size_input))
        self.x_test  = np.reshape(self.x_test , (self.x_test.shape [0], lookback, self.size_input))

        #self.x_train, self.y_train = create_dataset(self.x_train, self.y_train, look_back = lookback)
        #self.x_test , self.y_test  = create_dataset(self.x_test , self.y_test , look_back = lookback)


        print(f'after adding {lookback} dimension for lstm')
        print('self.x_train.shape=',self.x_train.shape)#format_to_lstm(df)
        print('self.x_test.shape=',self.x_test.shape)#format_to_lstm(df)


        model = Sequential()

        model.add(LSTM(units = size_hidden, activation=activation, return_sequences = True, input_shape = (lookback, self.size_input)))
        model.add(Dropout(dropout))

        model.add(LSTM(units = size_hidden, activation=activation, return_sequences = True))
        model.add(Dropout(dropout))

        model.add(LSTM(units = size_hidden, activation=activation, return_sequences=False))
        model.add(Dropout(dropout))

        model.add(Dense  (units=self.size_output, activation=activation))
        #model.summary()

        self._model_compile(model, optimizer=optimizer,  loss=loss, lr=lr, rho=rho, epsilon=epsilon, decay=decay)

        return model


    # |--------------------------------------------------------|
    # |                                                  ,       |
    # |--------------------------------------------------------|
    @staticmethod
    def _model_compile(model,  optimizer='rmsprop', loss='categorical_crossentropy', lr=0.00001, rho=0.9, epsilon=None, decay=0.0):
        model.compile( loss=loss  # measure how accurate the model during training
                      ,optimizer=optimizer#RMSprop(lr=lr, rho=rho, epsilon=epsilon, decay=decay)  # this is how model is updated based on data and loss function
                      # ,metrics=[precision_threshold(0.5)#, precision_threshold(0.2),precision_threshold(0.8)
                      #            , recall_threshold(0.5)#,    recall_threshold(0.2),   recall_threshold(0.8)
                      #           ]#https://stackoverflow.com/questions/42606207/keras-custom-decision-threshold-for-precision-and-recall
                       ,metrics=['accuracy']
                       )

    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def model_fit(self, model, epochs=100, batch_size=128, verbose=0)->History:
        return model.fit(self.x_train,
                         self.y_train,
                         batch_size=batch_size,
                         epochs=epochs,
                         validation_data=(self.x_test, self.y_test),
                         #validation_split = 0.1,
                         verbose=verbose)

    def model_weights(self, model, x, y, feature_names ):
        perm = PermutationImportance(model, random_state=1).fit(x, y)
        weights = eli5.formatters.as_dataframe.explain_weights_df(perm, feature_names=feature_names)
        print('\nweights=',weights)
    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def plot_evaluation(self, history ):
        print(f'\nsize.model.features(size_input) = {self.size_input}')
        print(f'\nsize.model.target  (size_output)= {self.size_output}')
        print('\nplot_accuracy_loss_vs_time...')
        history_dict = history.history
        print(history_dict.keys())
        file_name=f'files/output/{self.params}_accuracy.png'
        plot_stat_loss_vs_accuracy(history_dict, title=f'{self.params}_accuracy')
        hist = pd.DataFrame(history.history)
        hist['epoch'] = history.epoch
        print(hist.tail())


    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def model_evaluate(self, model, x, y):
        score = model.evaluate(x,y,  verbose=0)
        print(f'Test loss:    {score[0]} (is it close to 0 ?)')
        print(f'Test accuracy:{score[1]} (is it close to 1 and close to train accuracy ?)')
        if self.size_output == 2:
           print(f'null accuracy={max(y.mean(), 1 - y.mean())}')# # calculate null accuracy (for multi-class classification problems)
#        elif self.size_output > 2:
 #           print(f'null accuracy={y.value_counts().head(1) / len(y)}')## calculate null accuracy (for multi-class classification problems)



    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def model_predict(self, model,   model_type='xxx'):
        dfs = [self.x_train, self.x_test]

        x_all = pd.concat(dfs)
        #x_all = np.concatenate(dfs, axis=0)
        y_pred_proba_all = model.predict(x_all)
        y_pred_proba     = model.predict(self.x_test)# same as probs  = model.predict_proba(self.x_test)
        y_pred_proba_r = y_pred_proba
        print(f'predicting test data for model: {model_type}')
        ##print(f'labeled   as { self.y_test[0]}. (highest confidence for index {np.argmax( self.y_test[0])})')
        ##print(f'predicted as {y_pred_proba[0]}. (highest confidence for index {np.argmax(y_pred_proba[0])})')
#        print('y_train class distribution',self.y_train.value_counts(normalize=True))
         #print(pd.DataFrame(y_pred).describe())
        print(f'predicting train data')
        #print(f'labeled   as {     self.y_test[0]}. (highest confidence for index {np.argmax(     self.y_test[0])})')
        print(f'predicted as {y_pred_proba_all[0]}. (highest confidence for index {np.argmax(y_pred_proba_all[0])})')

        # print('Y_true[0]=',Y_true[0])
        # print('Y_pred[0]=',Y_pred[0])
        if model_type in self.models_need1hot:# and model_type != 'ker':
            if (model_type=='ker'):
                Y_pred = y_pred_proba

            else:
                y_pred_proba_r =   y_pred_proba[:, 1]
                Y_pred = np.argmax(y_pred_proba, axis=1)

            Y_true = np.argmax(self.y_test, axis=1)

            # if isinstance(y_pred_proba[0],(np.int64)):#for ker learn model
            #     print('probably ker')
            #     Y_pred = y_pred_proba
        else:
            Y_true = self.y_test
            Y_pred = y_pred_proba
            print('pred proba=',y_pred_proba[:4])

        print('Y_true[0:10]=',Y_true[0:10])#Y_true[0:10]= [1 1 0 1 0 0 0 0 0 1]
        print('Y_pred[0:10]=',Y_pred[0:10])#Y_pred[0:10]= [1 0 0 1 0 0 0 1 1 1]
        #if model_type in self.models_df:
        #print (f'type of Y_true is {Y_true.dtype}')#type(Y_true)
        if isinstance(Y_true, pd.Series) or isinstance(Y_true, pd.DataFrame):#  pd.Series
            Y_true = Y_true.values
            print('Y_true[0:10]=',Y_true[0:10])#Y_true[0:10]= [1 1 0 1 0 0 0 0 0 1]

        acc = accuracy_score(Y_true, Y_pred)
        if (self.size_output==2):
            f1  = f1_score      (Y_true, Y_pred)
            print("F1 Score : {0:0.4f} ".format(f1))
        print('\nmodel :',model_type)
        print('-------------------------')
        print("Accuracy : {0:0.2f} %".format(acc * 100))
        print(classification_report(Y_true,Y_pred))
        if self.size_output == 2:#multiclass format is not supported
            plot_roc     (Y_true, Y_pred, y_pred_proba_r   , file_name=f'files/output/{self.params}_roc.png')
        plot_conf_mtx    (Y_true, Y_pred, self.names_output, file_name=f'files/output/{self.params}_confusion.png')


        y_pred_proba_ok=[]
        for i, (p, t) in enumerate(zip(Y_pred,Y_true)):
            if p == t:
               y_pred_proba_ok.append(y_pred_proba_r[i])
        #       print(f'{i} ,{p} ,{t}, {y_pred_proba_r[i]} added' )
        #    else:
        #        print(f'{i} ,{p} ,{t}, {y_pred_proba_r[i]}')
        #print (f'len {len(y_pred_proba_ok)} > {len(y_pred_proba_r)} = {len(Y_pred)} = {len(Y_true)}' )
        #print('y_pred_proba_ok=',y_pred_proba_ok[:40])#[0.59, 0.41], dtype=float32), array([0.45, 0.55], dtype=float32), array([0.3, 0.7], dtype=float32), array([0.42, 0.58]
        plot_histogram(y_pred_proba_r   , 20, f'{self.params}_predAll', 'Predicted probability', 'Frequency', xmin=0, xmax=1)
        plot_histogram(y_pred_proba_ok  , 20, f'{self.params}_predOk', 'Predicted probability', 'Frequency', xmin=0, xmax=1)
#Y_true[0]= [1. 0.]
#Y_pred[0]= [0.4714 0.5286]






    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    def model_save(self, model)->str:
        print('\n======================================')
        print('\nSaving the model')
        print('\n======================================')
        folder = 'files/output/'
        print(f'\nSave model as {folder}model{self.params}.model')
        model.save(f'{folder}{self.params}.model')
        return 'ok'

    # |--------------------------------------------------------|
    # |                                                        |
    # |--------------------------------------------------------|
    @staticmethod
    def _plot_features_hstg(df_all):
        plot_histogram(x=df_all['range0']
                       , bins=100
                       , title='TA-diff bw open and close - Gaussian data '
                       , xlabel='range of a bar from open to close'
                       , ylabel='count')

        plot_histogram(x=df_all['range_sma']
                       , bins=100
                       , title='TA-diff bw 2 sma - Gaussian data'
                       , xlabel='diff bw 2 sma 10,20  '
                       , ylabel='count')



    #def _data_select_features(self, df):
    #print('\n======================================')
    #print('\nselecting features')
    #print('\n======================================')
    #elements = df.size
    #shape = df.shape
    #df_data = df.loc[:, self.names_input]
    #print(df_data.dtypes)

    # today = datetime.date.today()
    # file_name = self.symbol+'_prepared_'+str(today)+'.csv'
    # df_data.to_csv(file_name)
    #print('columns=', df_data.columns)
    #print('\ndata describe=\n', df_data.describe())
    #print(f'shape={str(shape)} >> {df_data.shape},  elements={str(elements)}, rows={str(shape[0])}')
    #return df_data