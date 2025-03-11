import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error
import plotly.express as px
import matplotlib.pyplot as plt
import os


def filter_users_by_rating_count(df, min_ratings=5, max_ratings=None):
    """
    Filters users based on their number of ratings.
    
    Args:
        df (pd.DataFrame): The dataset with user ratings.
        min_ratings (int): Minimum number of ratings a user must have to be included.
        max_ratings (int or None): Maximum number of ratings a user can have (None means no upper limit).
    
    Returns:
        pd.DataFrame: Filtered dataset with only users within the rating count range.
    """
    filtered_df = df.copy()
    user_counts = filtered_df['user_name'].value_counts()
    
    # Apply min/max thresholds
    if max_ratings is None:
        valid_users = user_counts[user_counts >= min_ratings].index
    else:
        valid_users = user_counts[(user_counts >= min_ratings) & (user_counts <= max_ratings)].index
        print(F'From {len(df.user_name.unique())} users, {len(valid_users)} have between {min_ratings} and {max_ratings} ratings')
    
    return filtered_df[filtered_df['user_name'].isin(valid_users)]



def plot_user_rating_distribution(df, bins=100):
    """Plots the distribution of number of ratings per user."""
    user_counts = df['user_name'].value_counts()

    plt.figure(figsize=(10, 5))
    plt.hist(user_counts, bins=bins, log=True, edgecolor='black', alpha=0.7)
    plt.xlabel("Number of Ratings per User")
    plt.ylabel("Count (Log Scale)")
    plt.title("Distribution of Ratings per User")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.show()


def downsample_to_minority(df):

    df_copy = df.copy()

    # Create a list of ratings and their desired sample sizes
    rating_counts = df_copy['rating'].value_counts()

    # Desired sample size for each class, using the median count as a target for all classes
    min_count = rating_counts.min()

    # Function to sample the dataframe to ensure balanced distribution
    def balanced_sample(df, target_count):
        return df.groupby('rating').apply(lambda x: x.sample(n=target_count, random_state=42)).reset_index(drop=True)

    # Apply the function to balance the sample
    df_balanced = balanced_sample(df_copy, target_count=min_count)

    return df_balanced


def hexbin_plot(df, epochs):
    # Ensure the "plots" directory exists
    os.makedirs("plots", exist_ok=True)

    # Create a list of ratings and their desired sample sizes
    rating_counts = df['rating'].value_counts()

    # Desired sample size for each class, using the median count as a target for all classes
    min_count = rating_counts.min()

    # Function to sample the dataframe to ensure balanced distribution
    def balanced_sample(df, target_count):
        return df.groupby('rating').apply(lambda x: x.sample(n=target_count, random_state=42)).reset_index(drop=True)

    # Apply the function to balance the sample
    df_balanced = balanced_sample(df, target_count=min_count)

    # Create hexbin plot with adjusted mincnt to balance color distribution
    plt.figure(figsize=(10, 6))
    hb = plt.hexbin(df_balanced['rating'], df_balanced['pred'], gridsize=50, cmap='Blues', mincnt=10)  # Adjust mincnt to filter out extreme density

    # Add a soft grid with lighter grid lines
    plt.grid(True, color='gray', linestyle='--', linewidth=0.5)

    # Add color bar for better understanding of density
    plt.colorbar(hb, label='Count in Bin')

    # Customize labels and title
    plt.xlabel('Actual Rating')
    plt.ylabel('Predicted Rating')
    plt.title(f'Actual vs Predicted Ratings (Balanced) - {epochs} Epochs')

    if epochs:
        # Save the plot with epochs in the filename
        filename = f"plots/hexbin_plot_{epochs}_epochs.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"Plot saved as {filename}")

    # Show the plot
    plt.show()


def plot_prediction_errors(df):
    # Calculate the prediction error
    df['error'] = df['rating'] - df['pred']

    # Calculate stats for the error distribution
    error_min = df['error'].min()
    error_max = df['error'].max()
    error_mean = df['error'].mean()
    error_median = df['error'].median()
    error_std = df['error'].std()

    # Calculate percentiles
    perc_25 = np.percentile(df['error'], 25)
    perc_75 = np.percentile(df['error'], 75)
    
    # Calculate IQR (Interquartile Range)
    Q1 = np.percentile(df['error'], 25)
    Q3 = np.percentile(df['error'], 75)
    IQR = Q3 - Q1

    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.hist(df['error'], bins=100, color='blue', alpha=0.7)
    plt.xlabel('Error (Actual - Predicted)')
    plt.ylabel('Frequency')
    plt.title('Distribution of Prediction Errors')

    # Add text box with statistics
    stats_text = (
        f"Mean Error: {error_mean:.3f}\n"
        f"Median Error: {error_median:.3f}\n"
        f"Std Dev of Errors: {error_std:.3f}\n"
        f"25th Percentile: {perc_25:.3f}\n"
        f"75th Percentile: {perc_75:.3f}\n"
        f"IQR: {IQR:.3f}\n"
        f"Min Error: {error_min:.3f}, Max Error: {error_max:.3f}"
    )
    
    # Add percentiles info to the title (you can adjust this to your preference)
    plt.figtext(0.15, 0.75, stats_text, fontsize=12, ha='left', va='top', bbox=dict(facecolor='white', alpha=0.7, edgecolor='gray', boxstyle='round,pad=0.5'))

    # Show the plot
    plt.show()


# Function to plot Average Error vs. Number of Titles Rated
def plot_avg_error_vs_num_ratings(df):
    # Copying the dataframe to avoid modifying the original
    df_copy = df.copy()
    df_copy['error'] = abs(df_copy['rating'] - df_copy['pred'])

    # Grouping by user_name
    user_stats = df_copy.groupby('user_name').agg(
        avg_error=('error', 'mean'),
        num_ratings=('item_title', 'count')
    )

    # Plotting the hexbin plot
    plt.figure(figsize=(8, 6))
    plt.hexbin(user_stats['num_ratings'], user_stats['avg_error'], gridsize=50, cmap='viridis')
    plt.colorbar(label='Number of Users')
    plt.title('Average Error vs Number of Titles Rated')
    plt.xlabel('Number of Titles Rated')
    plt.ylabel('Average Error')
    plt.ylim((0, 1.5))
    plt.show()


# Function to plot Average Error vs. Standard Deviation of Ratings
def plot_avg_error_vs_rating_variance(df):
    # Copying the dataframe to avoid modifying the original
    df_copy = df.copy()
    df_copy['error'] = abs(df_copy['rating'] - df_copy['pred'])

    # Grouping by user_name and calculating standard deviation of ratings
    user_ratings_std = df_copy.groupby('user_name')['rating'].std()

    # Calculating the average error
    user_stats = df_copy.groupby('user_name').agg(
        avg_error=('error', 'mean')
    )
    user_stats['rating_std'] = user_ratings_std

    # Plotting the hexbin plot
    plt.figure(figsize=(8, 6))
    plt.hexbin(user_stats['rating_std'], user_stats['avg_error'], gridsize=50, cmap='viridis')
    plt.colorbar(label='Number of Users')
    plt.title('Average Error vs Rating Variance (Stdev)')
    plt.xlabel('Standard Deviation of Ratings')
    plt.ylabel('Average Error')
    plt.xlim((0, 2))
    plt.ylim((0, 1.5))
    plt.show()


def plot_error_vs_num_ratings(df):
    """
    Creates an interactive scatter plot of mean absolute error vs. number of ratings per title.
    Hovering over each point shows the title, number of ratings, mean absolute error, mean rating, and color based on rating.

    Parameters:
    df (pd.DataFrame): DataFrame containing columns ['user_name', 'item_title', 'rating', 'pred']

    Returns:
    plotly.graph_objects.Figure: The interactive scatter plot
    """
    # Calculate the absolute error between rating and pred
    df['error'] = abs(df['rating'] - df['pred'])

    # Group by item_title, calculate:
    # - the number of unique ratings (users),
    # - the mean absolute error (mean_error),
    # - the mean rating for the film
    ratings_count = df.groupby('item_title').agg(
        num_ratings=('user_name', 'nunique'),  # Count unique users
        mean_error=('error', 'mean'),          # Calculate mean absolute error
        mean_rating=('rating', 'mean')         # Calculate mean rating
    ).reset_index()

    # Create the interactive plot using Plotly
    fig = px.scatter(ratings_count, 
                     x='num_ratings', 
                     y='mean_error', 
                     color='mean_rating',  # Assign colors based on the mean rating
                     color_continuous_scale='Viridis',  # You can choose any color scale you like
                     hover_data={'item_title': True, 'num_ratings': True, 'mean_error': True, 'mean_rating': True},
                     title="Mean Absolute Error vs. Number of Ratings per Title")

    return fig


def plot_error_distribution_with_counts(df):
    ratings = np.arange(0.5, 5.5, 0.5)  # Possible ratings from 0.5 to 5.0
    rmse_values = []
    mae_values = []
    counts = []

    for rating in ratings:
        # Filter rows where the rating is equal to the current rating
        rating_data = df[df['rating'] == rating]
        
        if len(rating_data) > 0:  # Only calculate if there are ratings for this star
            # Compute RMSE and MAE for the current rating group
            rmse = np.sqrt(mean_squared_error(rating_data['rating'], rating_data['pred']))
            mae = mean_absolute_error(rating_data['rating'], rating_data['pred'])
            count = len(rating_data)
        else:
            rmse = np.nan  # In case no data for this rating
            mae = np.nan
            count = 0
        
        rmse_values.append(rmse)
        mae_values.append(mae)
        counts.append(count)

    # Create a new DataFrame with the results
    error_df = pd.DataFrame({
        'rating': ratings,
        'RMSE': rmse_values,
        'MAE': mae_values,
        'count': counts
    })

    # Create an interactive plot with hover data, and size based on count
    fig = px.scatter(
        error_df,
        x='rating',
        y='RMSE',
        title='RMSE and MAE by Rating with Counts',
        labels={'rating': 'Rating', 'RMSE': 'Root Mean Squared Error (RMSE)'},
        hover_data={'rating': True, 'RMSE': True, 'MAE': True, 'count': True},  # Show RMSE, MAE, and count
        opacity=0.7,
        size='count',  # Set marker size based on count of ratings
        size_max=30,  # Limit the maximum size of the markers
        color='count',  # Color the points based on the count
        color_continuous_scale='Viridis'  # Color scale for better visualization
    )

    # Add MAE as a line
    fig.add_scatter(
        x=error_df['rating'],
        y=error_df['MAE'],
        mode='lines+markers',
        name='MAE',
        line=dict(color='red', dash='dot')
    )

    fig.show()

# Example usage:
# Assuming `df` is your DataFrame
# fig = plot_error_vs_num_ratings(df)
# fig.show()
