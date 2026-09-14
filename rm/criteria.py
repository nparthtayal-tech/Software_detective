"""Research-derived Reality Monitoring criterion catalogue.

Uses the commonly operationalized Sporer & Küpper family of eight
characteristics while explicitly acknowledging multiple RM models.
"""
CRITERIA = [
{"key":"clarity_vividness","name":"Clarity / vividness","model_family":"Sporer_Kupper","scoring":"intensity_0_2","research_direction":"external_memory_characteristic","description":"How clear, vivid, and perceptually rich the remembered account appears."},
{"key":"sensory_information","name":"Sensory information","model_family":"Sporer_Kupper","scoring":"frequency","research_direction":"external_memory_characteristic","description":"Visual, auditory, tactile, olfactory, gustatory, or other perceptual information."},
{"key":"spatial_information","name":"Spatial information","model_family":"Sporer_Kupper","scoring":"frequency","research_direction":"external_memory_characteristic","description":"Information about location, distance, position, direction, or spatial arrangement."},
{"key":"temporal_information","name":"Temporal information","model_family":"Sporer_Kupper","scoring":"frequency","research_direction":"external_memory_characteristic","description":"Information about when events occurred, sequence, duration, or temporal position."},
{"key":"affective_information","name":"Affective information","model_family":"Sporer_Kupper","scoring":"frequency","research_direction":"context_dependent","description":"Descriptions of emotions or feelings associated with the remembered event."},
{"key":"reconstructability","name":"Reconstructability","model_family":"Sporer_Kupper","scoring":"intensity_0_2","research_direction":"external_memory_characteristic","description":"Extent to which the account can be reconstructed from concrete information."},
{"key":"realism","name":"Realism","model_family":"Sporer_Kupper","scoring":"intensity_0_2","research_direction":"external_memory_characteristic","description":"Degree to which the described event is represented as concrete and plausible within its context."},
{"key":"cognitive_operations","name":"Cognitive operations","model_family":"Sporer_Kupper","scoring":"frequency","research_direction":"internal_memory_characteristic","description":"References to thinking, reasoning, imagining, deciding, inferring, planning, or other cognitive operations."},
]
