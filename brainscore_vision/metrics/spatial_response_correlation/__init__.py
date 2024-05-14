from brainscore_vision import metric_registry

from .spatial_correlation import SpatialCorrelationSimilarity, SpatialCharacterizationMetric
from .inter_individual_stats_ceiling import InterIndividualStatisticsCeiling

metric_registry['spatial_correlation'] = SpatialCorrelationSimilarity
metric_registry['spatial_characterization'] = SpatialCharacterizationMetric
metric_registry['inter_individual_statistics'] = InterIndividualStatisticsCeiling
