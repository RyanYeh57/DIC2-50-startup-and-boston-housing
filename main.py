"""Independent CRISP-DM regression workflows for two local CSV datasets."""
from pathlib import Path
import argparse
import json

ROOT = Path(__file__).resolve().parent
BOSTON = 'CRIM ZN INDUS CHAS NOX RM AGE DIS RAD TAX PTRATIO B LSTAT'.split()


def compare_models(X_train, X_test, y_train, y_test, preprocess, name, output, show):
    """Compare full-feature regressors on the same held-out observations."""
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    from sklearn.base import clone
    from sklearn.compose import TransformedTargetRegressor
    from sklearn.decomposition import PCA
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.feature_selection import SelectKBest, mutual_info_regression
    from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
    from sklearn.metrics import mean_squared_error, r2_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVR

    def mutual_scores(X, y):
        return mutual_info_regression(X, y, random_state=42)

    models = {
        'Linear Regression': LinearRegression(),
        'Ridge': Ridge(alpha=1.0),
        'LASSO': Lasso(alpha=0.01, max_iter=10000),
        'Elastic Net': ElasticNet(alpha=0.01, l1_ratio=0.5, max_iter=10000),
        'SVR (RBF)': SVR(C=10, epsilon=0.1),
        'SVR (Linear)': SVR(kernel='linear', C=10, epsilon=0.1),
        'PCA + Linear Regression': Pipeline([
            ('pca', PCA(n_components=0.95)), ('regression', LinearRegression())]),
        'Mutual Information + Linear': Pipeline([
            ('selection', SelectKBest(mutual_scores, k=min(3, X_train.shape[1]))),
            ('regression', LinearRegression())]),
        'Random Forest': RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=1),
        'Gradient Boosting': GradientBoostingRegressor(random_state=42),
    }
    horizontal = 'R&D Spend' if name == 'startups' else 'RM'
    x = X_test[horizontal].to_numpy()
    order = np.argsort(x, kind='stable')
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.scatter(x, y_test, color='black', s=35, label='Actual Data', zorder=5)
    rows = []
    predictions = pd.DataFrame({'x': x, 'actual': y_test.to_numpy()}, index=X_test.index)
    colors = plt.get_cmap('tab10')
    for index, (label, estimator) in enumerate(models.items()):
        pipeline = Pipeline([
            ('preprocess', clone(preprocess)),
            ('scale', StandardScaler()),
            ('regression', estimator),
        ])
        # Scale the target on training data too, so SVR/regularization are comparable.
        model = TransformedTargetRegressor(regressor=pipeline, transformer=StandardScaler())
        model.fit(X_train, y_train)
        values = model.predict(X_test)
        mse = float(mean_squared_error(y_test, values))
        rows.append({'Model': label, 'Features': ', '.join(X_train.columns),
                     'MSE': mse, 'RMSE': float(np.sqrt(mse)),
                     'R2 Score': float(r2_score(y_test, values))})
        predictions[label] = values
        ax.plot(x[order], values[order], linewidth=1.5, color=colors(index), label=label)
    ax.set(xlabel=horizontal, ylabel='Profit' if name == 'startups' else 'MEDV',
           title=f'{name}: Comparison of Different Regression Models (test set)')
    ax.legend(loc='best', fontsize=9)
    ax.grid(alpha=0.15)
    fig.text(0.5, 0.015, 'All input features used; lines connect test predictions sorted by the horizontal feature.',
             ha='center', fontsize=9)
    fig.tight_layout(rect=[0, 0.035, 1, 1])
    fig.savefig(output / 'model_comparison.png', dpi=180, bbox_inches='tight')
    if not show:
        plt.close(fig)
    results = pd.DataFrame(rows).sort_values('MSE').reset_index(drop=True)
    results.to_csv(output / 'model_comparison.csv', index=False)
    predictions.to_csv(output / 'model_comparison_predictions.csv', index_label='row')
    cells = [[row['Model'], f'{row["MSE"]:.4f}', f'{row["RMSE"]:.4f}', f'{row["R2 Score"]:.6f}']
             for row in results.to_dict('records')]
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.axis('off')
    ax.set_title(f'{name}: Test Results Sorted by MSE', pad=16)
    table = ax.table(cellText=cells, colLabels=['Model', 'MSE', 'RMSE', 'R2 Score'],
                     colWidths=[0.46, 0.2, 0.18, 0.16], cellLoc='left', bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for (row, column), cell in table.get_celld().items():
        cell.set_linewidth(0)
        cell.set_facecolor('#e6edf4' if row == 0 else '#f3f4f5' if row % 2 else 'white')
        if row == 0:
            cell.set_text_props(weight='bold')
    fig.savefig(output / 'model_comparison_table.png', dpi=180, bbox_inches='tight')
    if not show:
        plt.close(fig)
    print(f'\n[{name}] Model comparison (test set, sorted by MSE):')
    print(results[['Model', 'MSE', 'RMSE', 'R2 Score']].to_string(index=False))
    return results.to_dict('records')


def analyze(path, name, output, show=False):
    import joblib
    import matplotlib
    if not show:
        matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    from sklearn.compose import ColumnTransformer
    from sklearn.dummy import DummyRegressor
    from sklearn.feature_selection import f_regression
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import KFold, cross_val_score, train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    # 1. Business understanding: each dataset has its own prediction goal.
    target = 'Profit' if name == 'startups' else 'MEDV'
    numeric = ['R&D Spend', 'Administration', 'Marketing Spend'] if name == 'startups' else BOSTON
    categorical = ['State'] if name == 'startups' else []
    objective = 'Predict startup profit from spending and state.' if name == 'startups' else 'Predict Boston Housing MEDV from explanatory variables.'
    expected = numeric + categorical + [target]

    # 2. Data understanding: validate schema and summarize observed data.
    df = pd.read_csv(path)
    aliases = {c.lower(): c for c in expected}
    df.columns = [aliases.get(str(c).strip().lower(), str(c).strip()) for c in df.columns]
    if df.columns.duplicated().any():
        raise ValueError(f'{path}: duplicate column names')
    missing = sorted(set(expected) - set(df.columns))
    if missing:
        raise ValueError(f'{path}: missing columns {missing}')
    df = df[expected].copy()
    original_rows = len(df)
    for c in numeric + [target]:
        df[c] = pd.to_numeric(df[c], errors='raise')
    df[numeric + [target]] = df[numeric + [target]].replace([np.inf, -np.inf], np.nan)
    for c in categorical:
        df[c] = df[c].map(lambda v: str(v).strip() if pd.notna(v) else np.nan).replace('', np.nan)
    missing_values = df.isna().sum().to_dict()
    duplicates = int(df.duplicated().sum())

    # 3. Preparation: deduplicate, remove missing targets, split before fitting.
    df = df.drop_duplicates().dropna(subset=[target])
    if len(df) < 15:
        raise ValueError(f'{path}: at least 15 usable rows required')
    X, y = df[numeric + categorical], df[target]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    empty = X_train.columns[X_train.isna().all()].tolist()
    if empty:
        raise ValueError(f'{path}: training columns have no values: {empty}')
    transforms = [('numeric', SimpleImputer(strategy='median'), numeric)]
    if categorical:
        transforms.append(('categorical', Pipeline([
            ('impute', SimpleImputer(strategy='most_frequent')),
            ('encode', OneHotEncoder(drop='first', handle_unknown='ignore', sparse_output=False)),
        ]), categorical))

    # 4. Modeling: all specified predictors, with a mean baseline for comparison.
    model = Pipeline([
        ('preprocess', ColumnTransformer(transforms, verbose_feature_names_out=False)),
        ('regression', LinearRegression()),
    ])
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_rmse = np.sqrt(-cross_val_score(model, X_train, y_train, cv=cv, scoring='neg_mean_squared_error'))
    model.fit(X_train, y_train)
    baseline = DummyRegressor(strategy='mean').fit(X_train, y_train)

    # 5. Evaluation: untouched test set, baseline comparison, residual diagnostics.
    predicted = model.predict(X_test)
    def metrics(values):
        return {'R2': float(r2_score(y_test, values)),
                'MAE': float(mean_absolute_error(y_test, values)),
                'RMSE': float(np.sqrt(mean_squared_error(y_test, values)))}
    scores = metrics(predicted)
    baseline_scores = metrics(baseline.predict(X_test))
    success = scores['RMSE'] < baseline_scores['RMSE']
    output.mkdir(parents=True, exist_ok=True)
    df.describe(include='all').to_csv(output / 'data_summary.csv')
    pd.DataFrame({'actual': y_test, 'predicted': predicted, 'residual': y_test - predicted}).to_csv(output / 'test_predictions.csv', index_label='row')
    features = model.named_steps['preprocess'].get_feature_names_out()
    pd.Series(model.named_steps['regression'].coef_, index=features, name='coefficient').to_csv(output / 'coefficients.csv')

    # Exploratory feature-count comparison; rank only on training observations.
    train_encoded = model.named_steps['preprocess'].transform(X_train)
    test_encoded = model.named_steps['preprocess'].transform(X_test)
    feature_scores, _ = f_regression(train_encoded, y_train)
    ranking = np.argsort(-np.nan_to_num(feature_scores, nan=-np.inf), kind='stable')
    comparison = []
    browser_models = []
    for count in range(1, len(features) + 1):
        selected = ranking[:count]
        candidate = LinearRegression().fit(train_encoded[:, selected], y_train)
        candidate_scores = metrics(candidate.predict(test_encoded[:, selected]))
        browser_models.append({
            'count': count, 'features': features[selected].tolist(),
            'coefficients': candidate.coef_.tolist(), 'intercept': float(candidate.intercept_),
            'metrics': candidate_scores,
        })
        comparison.append({
            'Number of Features': count,
            'Selected Features': '[' + ', '.join(features[selected]) + ']',
            'RMSE': candidate_scores['RMSE'],
            'R-squared': candidate_scores['R2'],
        })
    comparison_df = pd.DataFrame(comparison)
    comparison_df.to_csv(output / 'feature_comparison.csv', index=False)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, metric in zip(axes, ['RMSE', 'R-squared']):
        ax.plot(comparison_df['Number of Features'], comparison_df[metric], 'o-', color='#287db5')
        ax.set(xlabel='Number of Features', ylabel=metric,
               title=f'{metric} by Number of Features')
        ax.set_xticks(comparison_df['Number of Features'])
        ax.grid(alpha=0.2)
    fig.suptitle(f'{name}: exploratory test-set comparison', fontsize=12)
    fig.tight_layout()
    fig.savefig(output / 'feature_performance.png', dpi=180, bbox_inches='tight')
    if not show:
        plt.close(fig)

    # Render a shareable table image with wrapped feature names.
    import textwrap
    table_rows = [[str(row['Number of Features']),
                   textwrap.fill(row['Selected Features'], width=72),
                   f'{row["RMSE"]:.6f}', f'{row["R-squared"]:.6f}']
                  for row in comparison]
    row_lines = [max(1, cells[1].count('\n') + 1) for cells in table_rows]
    total_units = 1.5 + sum(lines + 0.6 for lines in row_lines)
    fig, ax = plt.subplots(figsize=(15, total_units * 0.32 + 0.8))
    ax.axis('off')
    ax.set_title(f'{name}: feature selection results (test set)', pad=16)
    table = ax.table(cellText=table_rows, colLabels=comparison_df.columns,
                     colWidths=[0.15, 0.61, 0.12, 0.12], cellLoc='left', bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for (row, column), cell in table.get_celld().items():
        cell.set_linewidth(0)
        if row == 0:
            cell.set_text_props(weight='bold')
            cell.set_facecolor('#e6edf4')
            cell.set_height(1.5 / total_units)
        else:
            cell.set_height((row_lines[row - 1] + 0.6) / total_units)
            cell.set_facecolor('#f3f4f5' if row % 2 else 'white')
    fig.savefig(output / 'feature_comparison_table.png', dpi=180, bbox_inches='tight')
    if not show:
        plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].scatter(y_test, predicted)
    low, high = min(y_test.min(), predicted.min()), max(y_test.max(), predicted.max())
    axes[0].plot([low, high], [low, high], '--', color='gray')
    axes[0].set(xlabel='Actual', ylabel='Predicted', title='Test predictions')
    axes[1].scatter(predicted, y_test - predicted)
    axes[1].axhline(0, color='gray', linestyle='--')
    axes[1].set(xlabel='Predicted', ylabel='Residual', title='Test residuals')
    fig.tight_layout()
    fig.savefig(output / 'regression_diagnostics.png', dpi=160)
    if not show:
        plt.close(fig)

    # 6. Deployment: save/reload the full pipeline and verify its predictions.
    from feature_selection import compare_feature_methods
    print(f'[{name}] Computing five feature-selection methods...', flush=True)
    feature_methods = compare_feature_methods(
        model.named_steps['preprocess'], X_train, X_test, y_train, y_test, output,
    )
    model_comparison = compare_models(
        X_train, X_test, y_train, y_test, model.named_steps['preprocess'],
        name, output, show,
    )
    joblib.dump(model, output / 'model.joblib')
    restored = joblib.load(output / 'model.joblib')
    np.testing.assert_allclose(restored.predict(X_test), predicted)
    example = X_test.head(1)
    example.to_csv(output / 'prediction_input.csv', index=False)
    report = {
        'dataset': name, 'source': str(path), 'objective': objective,
        'success_criterion': 'Test RMSE below training-mean baseline (exploratory).',
        'original_rows': original_rows, 'usable_rows': len(df),
        'duplicate_rows': duplicates, 'missing_values_before_cleaning': missing_values,
        'train_rows': len(X_train), 'test_rows': len(X_test),
        'training_cv_RMSE_mean': float(cv_rmse.mean()),
        'training_cv_RMSE_std': float(cv_rmse.std()),
        'test_metrics': scores, 'baseline_test_metrics': baseline_scores,
        'model_comparison': model_comparison,
        'model_comparison_note': 'Default model configurations, trained on identical training data; test ranking is descriptive and not used to select the saved model. All predictors used; plot lines connect sorted test predictions, not a one-variable response curve.',
        'feature_comparison': comparison,
        'browser_feature_models': browser_models,
        'feature_methods': feature_methods,
        'feature_methods_note': 'Five training-only selection methods with OLS refit. Forward SFS and Exhaustive optimize training CV MSE; test metrics are descriptive. CV of a fixed selected subset is not nested CV and may be optimistic after search. Saved deployment model remains full-feature OLS.',
        'browser_preprocessing': {
            'numeric': numeric,
            'numeric_medians': dict(zip(numeric, model.named_steps['preprocess'].named_transformers_['numeric'].statistics_.tolist())),
            'categorical': categorical,
            'categories': {column: model.named_steps['preprocess'].named_transformers_['categorical'].named_steps['encode'].categories_[index].tolist()
                           for index, column in enumerate(categorical)},
        },
        'feature_comparison_note': 'Features ranked using training-only F scores. Test curves are exploratory; do not choose a final feature count using test results. Saved model retains all features.',
        'meets_exploratory_criterion': success,
        'interpretation': 'Improves on baseline.' if success else 'Does not improve on baseline; revisit features and modeling.',
        'limitations': 'One random test split; no causal conclusions or production readiness established. Review data provenance and intended use.',
        'reloaded_example_prediction': float(restored.predict(example)[0]),
    }
    (output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'[{name}] {scores}; baseline RMSE={baseline_scores["RMSE"]:.4f}')
    print(f'Report: {output / "report.json"}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', choices=['all', 'startups', 'boston'], default='all')
    parser.add_argument('--startups', type=Path, default=ROOT / '50_Startups.csv')
    parser.add_argument('--boston', type=Path, default=ROOT / 'BostonHousing.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs')
    parser.add_argument('--show', action='store_true', help='Open interactive Matplotlib windows after analysis; close windows to exit.')
    args = parser.parse_args()
    jobs = [(name, path) for name, path in [('startups', args.startups), ('boston', args.boston)] if args.dataset in ('all', name)]
    missing = [str(path) for _, path in jobs if not path.is_file()]
    if missing:
        parser.error('Missing CSV files: ' + ', '.join(missing) + '. Use --startups / --boston to supply paths.')
    for name, path in jobs:
        analyze(path, name, args.output / name, show=args.show)
    if args.show:
        import matplotlib.pyplot as plt
        print('Close all chart windows to exit.')
        plt.show()


if __name__ == '__main__':
    main()
