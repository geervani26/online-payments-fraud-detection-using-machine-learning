# IMPORTING LIBRARIES
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier
import pickle
import os

# READ THE DATASET

df = pd.read_csv("data/PS_20174392719_1491204439457_log.csv", nrows=2000)

print("Class Distribution:\n", df['isFraud'].value_counts())

# DATA PREPROCESSING

df = df.drop(['nameOrig', 'nameDest', 'isFlaggedFraud'], axis=1)

le = LabelEncoder()
df['type'] = le.fit_transform(df['type'])

X = df.drop('isFraud', axis=1)
y = df['isFraud']

# TRAIN TEST SPLIT (STRATIFIED)

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)


# RANDOM FOREST

rf = RandomForestClassifier(
    n_estimators=200,
    class_weight='balanced',
    random_state=42
)

rf.fit(X_train, y_train)
rf_pred = rf.predict(X_test)

print("\n=== Random Forest ===")
print("Accuracy:", accuracy_score(y_test, rf_pred))
print(confusion_matrix(y_test, rf_pred))
print(classification_report(y_test, rf_pred))


# DECISION TREE

dt = DecisionTreeClassifier(
    class_weight='balanced',
    random_state=42
)

dt.fit(X_train, y_train)
dt_pred = dt.predict(X_test)

print("\n=== Decision Tree ===")
print("Accuracy:", accuracy_score(y_test, dt_pred))
print(confusion_matrix(y_test, dt_pred))
print(classification_report(y_test, dt_pred))


# EXTRA TREES

et = ExtraTreesClassifier(
    n_estimators=200,
    class_weight='balanced',
    random_state=42
)

et.fit(X_train, y_train)
et_pred = et.predict(X_test)

print("\n=== Extra Trees ===")
print("Accuracy:", accuracy_score(y_test, et_pred))
print(confusion_matrix(y_test, et_pred))
print(classification_report(y_test, et_pred))


# SUPPORT VECTOR MACHINE (GUIDE STYLE BUT IMPROVED)

svc = Pipeline([
    ("scaler", StandardScaler()),
    ("svc", SVC(
        kernel='rbf',
        C=2,
        gamma='scale',
        class_weight='balanced'
    ))
])

svc.fit(X_train, y_train)

svc_train_pred = svc.predict(X_train)
svc_test_pred = svc.predict(X_test)

print("\n=== Support Vector Machine ===")
print("Train Accuracy:", accuracy_score(y_train, svc_train_pred))
print("Test Accuracy:", accuracy_score(y_test, svc_test_pred))
print(confusion_matrix(y_test, svc_test_pred))
print(classification_report(y_test, svc_test_pred))


# XGBOOST

scale_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1])

xgb = XGBClassifier(
    eval_metric='logloss',
    random_state=42,
    scale_pos_weight=scale_weight,
    n_estimators=200,
    learning_rate=0.1
)

xgb.fit(X_train, y_train)
xgb_pred = xgb.predict(X_test)

print("\n=== XGBoost ===")
print("Accuracy:", accuracy_score(y_test, xgb_pred))
print(confusion_matrix(y_test, xgb_pred))
print(classification_report(y_test, xgb_pred))


# CROSS VALIDATION (LIKE GUIDE)

print("\n=== Cross Validation (5 Fold) ===")

models = {
    "RandomForest": rf,
    "DecisionTree": dt,
    "ExtraTrees": et,
    "SVC": svc,
    "XGBoost": xgb
}

for name, model in models.items():
    scores = cross_val_score(model, X, y, cv=5)
    print(f"{name} CV Accuracy: {scores.mean():.4f}")


# SAVE SVC

os.makedirs("model", exist_ok=True)
pickle.dump(svc, open("model/payments.pkl", "wb"))


print("\nModel Saved Successfully!")
