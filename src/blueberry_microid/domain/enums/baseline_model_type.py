from enum import Enum


class BaselineModelType(str, Enum):
    MAJORITY_CLASS = "majority_class"
    LOGISTIC_REGRESSION_TABULAR = "logistic_regression_tabular"
