# pip install "transformers>=4.44" accelerate "outlines[transformers]>=1.2.0" "pydantic>=2"
from pathlib import Path
import os
import pandas as pd
# file_path = Path("..") / "Predictions" / "your_file.txt"



import lib

if __name__ == "__main__":

    dir_predictions = os.path.join("Predictions")
    dir_GT = os.path.join( "GT")

    path_gt = os.path.join(dir_GT, "GT_gpt5_2_1.xlsx")

    prediction_files = os.listdir(dir_predictions)

    print(prediction_files)

    for file in prediction_files:

        path_pred = os.path.join(dir_predictions, file)

        df = lib.evaluate_categorical_metrics(
        path_pred=path_pred,
        path_gt=path_gt,
        metrics=("AccAll", "AccPresent", "AccNull", "GoldCoverage"),
        )
        # Save to Excel file with sheet named after the prediction file
        excel_file = "metrics.xlsx"
        sheet_name = Path(file).stem.replace("predictions_", "")  # Get filename without extension and remove prefix
        
        if os.path.exists(excel_file):
            with pd.ExcelWriter(excel_file, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        else:
            df.to_excel(excel_file, sheet_name=sheet_name, index=False)
