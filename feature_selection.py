"""Training-only feature selection and held-out OLS evaluation."""
from itertools import combinations


def compare_feature_methods(preprocess, X_train, X_test, y_train, y_test, output):
    import numpy as np
    import pandas as pd
    from sklearn.base import clone
    from sklearn.feature_selection import RFE, f_regression
    from sklearn.linear_model import ElasticNet, Lasso, LinearRegression
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import KFold
    from sklearn.preprocessing import StandardScaler

    train = preprocess.transform(X_train)
    test = preprocess.transform(X_test)
    names = preprocess.get_feature_names_out()
    p = len(names)
    if p > 13:
        raise ValueError('Exact exhaustive search is limited to 13 encoded predictors.')
    scaled = StandardScaler().fit_transform(train)
    target = np.asarray(y_train)
    target_scaled = StandardScaler().fit_transform(target[:, None]).ravel()
    f_scores, _ = f_regression(scaled, target)
    f_scores = np.nan_to_num(f_scores)

    # Fit preprocessing afresh within every training CV fold. Fix category
    # vocabulary to the outer training vocabulary to keep feature indices stable.
    folds = []
    for fit_indices, valid_indices in KFold(5, shuffle=True, random_state=42).split(X_train):
        fold_preprocess = clone(preprocess)
        if 'categorical' in preprocess.named_transformers_:
            categories = preprocess.named_transformers_['categorical'].named_steps['encode'].categories_
            fold_preprocess.set_params(categorical__encode__categories=categories)
        fit = fold_preprocess.fit_transform(X_train.iloc[fit_indices])
        valid = fold_preprocess.transform(X_train.iloc[valid_indices])
        # Scaling improves numerical stability of the least-squares solver.
        scaler = StandardScaler().fit(fit)
        folds.append((scaler.transform(fit), scaler.transform(valid),
                      target[fit_indices], target[valid_indices]))
    score_cache = {}

    def cv_mse(indices):
        key = tuple(sorted(indices))
        if key not in score_cache:
            losses = []
            for fit, valid, fit_y, valid_y in folds:
                design = np.column_stack((np.ones(len(fit)), fit[:, key]))
                weights = np.linalg.lstsq(design, fit_y, rcond=None)[0]
                predicted = np.column_stack((np.ones(len(valid)), valid[:, key])) @ weights
                losses.append(float(np.mean((valid_y - predicted) ** 2)))
            score_cache[key] = float(np.mean(losses))
        return score_cache[key]

    subsets = {}
    descriptions = {
        'Lasso': 'Standardized Lasso coefficient ranking (alpha=0.01), then OLS refit.',
        'Forward SFS': 'Greedy forward selection minimizing five-fold training CV MSE.',
        'RFE': 'Recursive elimination using standardized linear regression coefficients.',
        'ElasticNet': 'Standardized ElasticNet coefficient ranking (alpha=0.01, l1_ratio=0.5), then OLS refit.',
        'Exhaustive': 'All subsets at each k; minimize five-fold training CV MSE, then OLS refit.',
    }
    for label, estimator in [('Lasso', Lasso(alpha=0.01, max_iter=20000)),
                             ('ElasticNet', ElasticNet(alpha=0.01, l1_ratio=0.5, max_iter=20000))]:
        estimator.fit(scaled, target_scaled)
        # Resolve zero/tied coefficient magnitudes with training-only F scores.
        rank = np.lexsort((np.arange(p), -f_scores, -np.abs(estimator.coef_)))
        subsets[label] = [rank[:k].tolist() for k in range(1, p + 1)]
    forward = []
    subsets['Forward SFS'] = []
    for k in range(1, p + 1):
        added = min((i for i in range(p) if i not in forward),
                    key=lambda i: (cv_mse(forward + [i]), i))
        forward.append(added)
        subsets['Forward SFS'].append(forward.copy())
    subsets['RFE'] = []
    for k in range(1, p + 1):
        selector = RFE(LinearRegression(), n_features_to_select=k, step=1).fit(scaled, target_scaled)
        subsets['RFE'].append(np.flatnonzero(selector.support_).tolist())
    print(f'  Exhaustive search: {2 ** p - 1} subsets, 5 training CV folds', flush=True)
    subsets['Exhaustive'] = []
    for k in range(1, p + 1):
        best = min(combinations(range(p), k), key=lambda indices: (cv_mse(indices), indices))
        subsets['Exhaustive'].append(list(best))

    methods, rows = {}, []
    for label in descriptions:
        models = []
        for indices in subsets[label]:
            model = LinearRegression().fit(train[:, indices], target)
            predicted = model.predict(test[:, indices])
            metrics = {'RMSE': float(np.sqrt(mean_squared_error(y_test, predicted))),
                       'MAE': float(mean_absolute_error(y_test, predicted)),
                       'R2': float(r2_score(y_test, predicted))}
            cv_rmse = float(np.sqrt(cv_mse(indices)))
            record = {'count': len(indices), 'features': names[indices].tolist(),
                      'coefficients': model.coef_.tolist(), 'intercept': float(model.intercept_),
                      'metrics': metrics, 'training_cv_RMSE': cv_rmse}
            models.append(record)
            rows.append({'Method': label, 'Number of Features': len(indices),
                         'Selected Features': ', '.join(record['features']),
                         'Training CV RMSE': cv_rmse, 'RMSE': metrics['RMSE'],
                         'MAE': metrics['MAE'], 'R-squared': metrics['R2']})
        recommended = min(models, key=lambda m: (m['training_cv_RMSE'], m['count']))['count']
        methods[label] = {'description': descriptions[label], 'models': models,
                          'training_cv_preferred_count': recommended}
    pd.DataFrame(rows).to_csv(output / 'feature_methods.csv', index=False)
    return methods
