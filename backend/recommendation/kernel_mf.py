import pandas as pd
import numpy as np
import random
import mlflow

# Modeling
from matrix_factorization import KernelMF, train_update_test_split
from backend.recommendation.utils import filter_users_by_rating_count
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split, GridSearchCV, ParameterGrid

pd.options.display.max_rows = 100
pd.set_option('display.max_colwidth', None)
rand_seed = 2
np.random.seed(rand_seed)
random.seed(rand_seed)


class MF_Recommender():
    def __init__(self, movie_data, config):
        self.movie_data = movie_data
        self.config = config
        
        self.user_name2id = {name: idx for idx, name in enumerate(sorted(movie_data['user_name']))}
        self.id2username = {idx: name for name, idx in self.user_name2id.items()}
        self.filmid2title = dict(zip(movie_data['item_id'], movie_data['alt_title']))

    def _assign_user_id(self, data):
        data['user_id'] = data['user_name'].map(self.user_name2id)
        return data

    def _downsample_titles(self, data):
        print(f'downsampling to the top {self.config["top_n_titles"]} titles')
        top_n_titles = self.config.get('top_n_titles', self.config.get('top_n_titles', 500))
        top_films = data["item_id"].value_counts().nlargest(top_n_titles).index
        return data[data["item_id"].isin(top_films)]

    def _downsample_members(self, data, top_n_members):
        print(f'downsampling to the top {top_n_members} members')
        top_n_members = data["user_id"].value_counts().nlargest(top_n_members).index
        return data[data["user_id"].isin(top_n_members)]

    def prepare_data(self, top_n_members=None):

        self.movie_data = self._downsample_titles(self.movie_data)
        self.movie_data = self._assign_user_id(self.movie_data)
        if top_n_members:
            self.movie_data = self._downsample_members(self.movie_data, top_n_members)

        X = self.movie_data[['user_id', 'item_id']]
        y = self.movie_data['rating']

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=self.config.get('test_size', 0.2)
        )

        print(f'Dataset is of shape: {self.movie_data.shape}]')

    def train(self, single_run_tag):
        with mlflow.start_run():
            mlflow.log_params(self.config)
            mlflow.log_param('single_run_tag', single_run_tag)
            mlflow.log_param('num_ratings', self.movie_data.shape[0])
            mlflow.log_param('num_members', len(self.movie_data.user_id.unique()))

            self.matrix_fact = KernelMF(
                n_epochs=self.config.get('n_epochs', 20),
                n_factors=self.config.get('n_factors', 100),
                kernel=self.config.get('kernel', 'linear'),
                verbose=self.config.get('verbose', 1),
                lr=self.config.get('lr', 0.001),
                # init_mean=self.config.get('init_mean', 0),
                # init_sd=self.config.get('init_sd', 0.1),
                reg=self.config.get('reg', 0.005),
                min_rating=self.config.get('min_rating', 1),
                max_rating=self.config.get('max_rating', 10)
            )
            
            self.matrix_fact.fit(self.X_train, self.y_train)

    def test(self):

        self.train_pred = self.matrix_fact.predict(self.X_train)
        train_rmse = mean_squared_error(self.y_train, self.train_pred)
        train_mae = mean_absolute_error(self.y_train, self.train_pred)
        print(f'\nTrain RMSE: {train_rmse:.4f}')
        print(f'Train MAE: {train_mae:.4f}')
        mlflow.log_metric('train_rmse', train_rmse)
        mlflow.log_metric('train_mae', train_mae)

        self.test_pred = self.matrix_fact.predict(self.X_test)
        test_rmse = mean_squared_error(self.y_test, self.test_pred)
        test_mae = mean_absolute_error(self.y_test, self.test_pred)

        print(f'\nTest RMSE: {test_rmse:.4f}')
        print(f'Test MAE: {test_mae:.4f}')
        mlflow.log_metric('test_rmse', test_rmse)
        mlflow.log_metric('test_mae', test_mae)

    def grid_search(self, param_grid, run_tag):
            
        # Start the parent run in MLflow to track all the trials
        with mlflow.start_run() as parent_run:
            mlflow.log_params(self.config)
            mlflow.log_param('run_tag', run_tag)
            mlflow.log_param('num_ratings', self.movie_data.shape[0])
            mlflow.log_param('num_members', len(self.movie_data.user_id.unique()))
            
            # Convert the param_grid to the form that GridSearchCV can accept
            grid = ParameterGrid(param_grid)

            best_rmse = float('inf')
            best_params = None

            # Iterate over each parameter combination in the grid
            for params in grid:
                # print(f"\nTesting parameters: {params}")
                # Start a new child run for each set of hyperparameters
                with mlflow.start_run(parent_run_id=parent_run.info.run_id, nested=True) as child_run:
                    # Log the hyperparameters
                    mlflow.log_params(params)
                    mlflow.log_param('run_tag', run_tag)
                    
                    # Set up the model with the current parameters
                    self.matrix_fact = KernelMF(
                        n_epochs=params['n_epochs'],
                        n_factors=params['n_factors'],
                        kernel=params['kernel'],
                        verbose=0,
                        lr=params['lr'],
                        reg=params['reg'],
                        min_rating=1,
                        max_rating=10
                    )

                    # Train the model
                    self.matrix_fact.fit(self.X_train, self.y_train)

                    # Predict and calculate RMSE
                    pred = self.matrix_fact.predict(self.X_test)
                    rmse = mean_squared_error(self.y_test, pred)
                    mae = mean_absolute_error(self.y_test, pred)
                    # print(f'RMSE: {rmse:.4f}')
                    
                    # Log RMSE to MLflow for the current child run
                    mlflow.log_metric('test_rmse', rmse)
                    mlflow.log_metric('test_mae', mae)
                    
                    # Track the best model
                    if rmse < best_rmse:
                        best_rmse = rmse
                        best_params = params

        # After completing the grid search, log the best parameters and RMSE to the parent run
        print(f"\nBest parameters: {best_params} with RMSE: {best_rmse:.4f}")
        mlflow.log_params(best_params)
        mlflow.log_metric('best_rmse', best_rmse)

    def get_recommendations(self, user_name):
        user_id = self.user_name2id[user_name]
        items_known = self.X_train.query('user_id == @user_id')['item_id']
        return self.matrix_fact.recommend(user=user_id, items_known=items_known)

    def update_and_recommend(self, user_history, exclude_known=True):
        temp_user_id = 999999999
        user_history = user_history.assign(user_id=temp_user_id)
        X_new = user_history[['user_id', 'item_id']]
        y_new = user_history['rating']

        if exclude_known:
            items_known = X_new['item_id']
        else:
            print('Note: including already seen items')
            items_known = None

        # print('Warning: not excluding known items from recommendation')
        self.matrix_fact.update_users(
            X_new, y_new, lr=self.config.get('lr', 0.001), 
            n_epochs=self.config.get('n_epochs', 20), verbose=self.config.get('verbose', 1)
        )

        recs = self.matrix_fact.recommend(user=temp_user_id, items_known=items_known, amount=-1, bound_ratings=True)
        return [{'user_id': x[0], 'item_id': x[1], 'prediction': x[2]} for x in recs.values]

    def get_test_results(self):

        self.filmid2title = dict(zip(self.movie_data['item_id'], self.movie_data['alt_title']))

        test_results = pd.DataFrame({
            'user_id': self.X_test['user_id'],
            'item_id': self.X_test['item_id'],
            'rating': self.y_test,
            'pred': self.test_pred
        })
        
        test_results['user_name'] = test_results['user_id'].map(self.id2username)
        test_results['item_title'] = test_results['item_id'].map(self.filmid2title)
        
        return test_results[['user_name', 'item_title', 'rating', 'pred']]