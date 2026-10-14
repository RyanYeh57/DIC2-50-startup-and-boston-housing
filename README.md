# CRISP-DM: 50 Startups 與 Boston Housing

兩個資料集各自建立模型，不合併資料。流程包含商業目標、資料摘要、清理與編碼、線性迴歸、評估及模型保存與載入驗證。

## 互動報告網頁

直接用瀏覽器開啟 `docs/index.html`，即可切換資料集、選取特徵數、查看係數、即時試算、開關模型圖例及下載分析資料。網站使用本機分析結果，無須外部圖表 CDN，也可離線開啟。

更新分析後重新匯出網頁：

```powershell
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe export_site.py
```

網站原始版面位於 `site/dist/`；匯出程式會更新資料與圖表，並同步至 GitHub Pages 可使用的 `docs/`。修改版面時請編輯 `site/dist/index.html`、`styles.css` 與 `app.js`，再執行匯出。

GitHub Pages 發佈檔案位於 `docs/`，需先推送到 GitHub，再將倉庫 Pages 的來源設為對應分支的 `/docs`。本次未替使用者更改 GitHub 倉庫設定。

## 執行

```powershell
python -m pip install -r requirements.txt
python main.py --startups .\50_Startups.csv --boston .\BostonHousing.csv
```

CSV 必須有標題列。50 Startups 欄位：`R&D Spend, Administration, Marketing Spend, State, Profit`。
Boston Housing 欄位：`CRIM, ZN, INDUS, CHAS, NOX, RM, AGE, DIS, RAD, TAX, PTRATIO, B, LSTAT, MEDV`。
欄位名稱不區分大小寫，會去除前後空白。Boston 的預測目標是 MEDV；請確認資料來源、單位與使用限制。

單獨執行：`python main.py --dataset startups` 或 `python main.py --dataset boston`。不同檔名可用 `--startups` 或 `--boston` 指定。

使用 Matplotlib 視窗顯示圖表（同時保存 PNG）：

```powershell
.\.venv\Scripts\python.exe main.py --show
```

可加上 `--dataset startups` 或 `--dataset boston` 只顯示其中一個資料集。圖表視窗可縮放、平移與另存圖片；關閉所有圖表視窗後程式結束。不加 `--show` 時只保存檔案。

## 評估與產物

每個資料集的結果分別放在 `outputs/startups/` 和 `outputs/boston/`，包含資料摘要、係數、測試預測、診斷圖、模型、預測輸入示例與 `report.json`。

先刪除完全重複資料與缺失目標，再切分 80% 訓練／20% 測試資料。前處理只在訓練資料擬合，五折交叉驗證也會重新擬合完整 Pipeline。保留全部指定特徵，避免缺乏依據地固定選三個特徵。

報告包含 R2、MAE、RMSE、訓練集交叉驗證，以及訓練平均值基準比較。探索性成功標準是測試 RMSE 低於基準；正式用途仍需定義業務誤差門檻、補上資料來源與分析解讀，規劃模型監控與更新。單次切分不能保證泛化能力，係數不代表因果關係。

## 特徵數量比較圖

每個資料集另輸出 `feature_comparison.csv`、表格圖片 `feature_comparison_table.png` 及雙折線圖 `feature_performance.png`，顯示特徵數量、所選特徵、測試 RMSE 與 R-squared。

以訓練資料的單變量 F 分數排序編碼後特徵，逐步增加特徵數量。State 的每個編碼欄位算一個特徵；目前採 drop='first'，因此 50 Startups 通常有五個編碼後特徵。此圖為測試集探索比較，不用來選擇正式模型的特徵數；保存的模型仍使用全部特徵。數值會依資料、切分及選取方法而不同。

## 多模型比較

自動比較 Linear Regression、Ridge、LASSO、Elastic Net、兩種核函數的 SVR、PCA + Linear Regression、Mutual Information + Linear Regression、Random Forest 與 Gradient Boosting。所有模型使用相同訓練／測試資料，前處理與輸入／目標標準化均只在訓練資料擬合，指標換回原始目標單位。

產出 `model_comparison.png`、`model_comparison_table.png`、依 MSE 排序的 `model_comparison.csv` 與逐筆 `model_comparison_predictions.csv`。50 Startups 橫軸為 R&D Spend，Boston Housing 為 RM。模型使用所有輸入特徵，折線連接依橫軸排序的測試預測，並非只改變單一變數的反應曲線。PCA 與 Mutual Information 是前處理／特徵選取方法，會搭配線性迴歸。

`--show` 同時顯示比較圖與結果表。模型採固定預設配置，測試集排序僅供比較；保存的部署模型仍為原本的全特徵線性迴歸。

## 使用已保存模型

僅載入自己產生或可信來源的模型。

```python
import joblib
import pandas as pd
model = joblib.load('outputs/startups/model.joblib')
rows = pd.read_csv('outputs/startups/prediction_input.csv')
print(model.predict(rows))
```
