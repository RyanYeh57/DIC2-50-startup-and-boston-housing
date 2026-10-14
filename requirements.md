# 專案需求：50 Startups 與 Boston Housing

## 目的

依 CRISP-DM 六階段，分別建立 50 Startups 的利潤預測模型與 Boston Housing 的 MEDV 預測模型。兩個資料集獨立訓練、評估及保存結果。

## 執行環境與套件

本機已使用 Python 3.14.3 通過合成資料流程測試；真實資料的分析結果仍需提供 CSV 後驗證。

| 套件 | requirements.txt 的限制 | 用途 |
| --- | --- | --- |
| pandas | 未固定版本 | CSV 讀取、資料清理與摘要 |
| numpy | 未固定版本 | 數值計算與預測一致性檢查 |
| scikit-learn | >=1.2 | 前處理、迴歸、交叉驗證與評估 |
| matplotlib | 未固定版本 | 預測與殘差診斷圖 |
| joblib | 未固定版本 | 保存及載入模型 Pipeline |

安裝套件使用 `requirements.txt`；本文件說明專案需求。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 資料集需求

兩份資料均須為有標題列的 CSV，欄位名稱不區分大小寫，允許前後空白。數值欄位須可轉換為數值；不得有正規化後重複的欄位名稱。

| 資料集 | 預設檔名 | 輸入特徵 | 預測目標 |
| --- | --- | --- | --- |
| 50 Startups | 50_Startups.csv | R&D Spend、Administration、Marketing Spend、State | Profit |
| Boston Housing | BostonHousing.csv | CRIM、ZN、INDUS、CHAS、NOX、RM、AGE、DIS、RAD、TAX、PTRATIO、B、LSTAT | MEDV |

每份資料移除完全重複紀錄及缺失目標後，至少須有 15 筆可用紀錄。訓練集內不得存在整欄缺失的輸入特徵。資料來源、欄位單位與使用限制需另行記錄。

## CRISP-DM 功能需求

| 階段 | 需求 |
| --- | --- |
| 商業理解 | 定義各資料集的預測目標，以測試 RMSE 低於訓練平均值基準作為探索性成功標準 |
| 資料理解 | 檢查必要欄位、缺失值、重複紀錄，輸出描述統計 |
| 資料準備 | 清理資料，依固定隨機種子 42 切分 80% 訓練與 20% 測試資料；數值以中位數填補，類別以眾數填補並做 One-Hot 編碼 |
| 建模 | 使用全部指定特徵建立多元線性迴歸 Pipeline，執行五折訓練集交叉驗證，建立平均值基準模型 |
| 評估 | 輸出測試 R2、MAE、RMSE、交叉驗證 RMSE 平均與標準差、基準比較、預測圖及殘差圖 |
| 部署 | 保存完整 Pipeline，重新載入並驗證預測一致性，提供一列預測輸入示例 |

前處理須只在訓練資料上擬合；交叉驗證每折須重新擬合完整 Pipeline，避免資料洩漏。

## 執行方式

同時執行兩個資料集：

```powershell
.\.venv\Scripts\python.exe main.py --startups .\50_Startups.csv --boston .\BostonHousing.csv
```

單獨執行其中一個：

```powershell
.\.venv\Scripts\python.exe main.py --dataset startups --startups .\50_Startups.csv
.\.venv\Scripts\python.exe main.py --dataset boston --boston .\BostonHousing.csv
```

可使用 `--output` 指定輸出資料夾，預設為專案內的 `outputs/`。

## 輸出與驗收

兩個資料集的結果分別存放在 `outputs/startups/` 與 `outputs/boston/`。

| 檔案 | 內容 |
| --- | --- |
| data_summary.csv | 清理後資料的描述統計 |
| coefficients.csv | 前處理後特徵的迴歸係數 |
| test_predictions.csv | 測試資料實際值、預測值及殘差 |
| regression_diagnostics.png | 實際值對預測值圖與殘差圖 |
| feature_comparison.csv | 各特徵數量的所選特徵、測試 RMSE 與 R-squared |
| feature_methods.csv | Lasso、Forward SFS、RFE、ElasticNet、Exhaustive Search 的各特徵數結果 |
| feature_comparison_table.png | 特徵數量比較表格圖片 |
| feature_performance.png | RMSE 與 R-squared 隨特徵數量變化的雙折線圖 |
| model_comparison.png | 測試資料實際值及十種模型配置的預測比較圖 |
| model_comparison_table.png | 依測試 MSE 排序的模型結果表 |
| model_comparison.csv | 模型、輸入欄位、MSE、RMSE、R2 Score |
| model_comparison_predictions.csv | 同一測試集各模型的逐筆預測 |
| model.joblib | 完整前處理與迴歸模型 |
| prediction_input.csv | 一列輸入示例，不含目標欄位 |
| report.json | 目標、資料品質、資料筆數、評估指標、基準比較及限制 |

驗收時須確認兩個真實資料集均能完成執行並產生上述檔案，模型重新載入後預測一致，報告可讀取且包含各項評估指標。執行成功與模型達成探索性成功標準為不同的驗收事項；若未優於基準，須如實記錄並重新檢討特徵及建模方式。

正式應用前仍需補上業務可接受的誤差門檻、真實資料結果解讀，以及模型監控與更新規劃。
