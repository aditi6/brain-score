import xarray as xr
import itertools
import re
from os import listdir
from pathlib import Path

import pandas as pd

import brainscore_vision
from brainio.assemblies import DataAssembly
from brainio.stimuli import StimulusSet


def collect_target_assembly(stimulus_class, perturbation_location) -> DataAssembly:
    """
    Load Data from path + subselect as specified by Experiment

    :return: DataAssembly
    """
    stimulus_set = _load_stimulus_set(stimulus_class)
    training_stimuli = _load_training_stimuli()
    stimulus_set_face_patch = _load_stimulus_set_face_patch()

    # make into DataAssembly
    data = _load_target_data(stimulus_class, perturbation_location)
    subject_assemblies = []
    for subject in sorted(set(data['subject'])):
        subject_data = data[data['subject'] == subject]
        subject_assembly = DataAssembly(data=[subject_data['accuracies']], dims=['subject', 'condition'],
                                        coords={'task': ('condition', subject_data['condition']),  # same vs. diff
                                                'object_name': ('condition', subject_data['object_name']),
                                                'current_pulse_mA': ('condition', subject_data['current_pulse_mA']),
                                                'subject': ('subject', [f"M{int(subject)}"]),
                                                },
                                        attrs={'stimulus_set': stimulus_set,
                                               'training_stimuli': training_stimuli,
                                               'stimulus_set_face_patch': stimulus_set_face_patch})
        subject_assemblies.append(subject_assembly)
    assembly = xr.concat(subject_assemblies, 'subject')
    return assembly


def _load_target_data(stimulus_class, perturbation_location):
    """
    From the Results section:
    "We first stimulated in the most anterior face patch, AM, previously shown
    to contain a view-invariant representation of individual identity3."

    "We report maximums across sessions because
    effect size correlated with accuracy of targeting to the center of the
    face patch and varied across sessions, as discussed in detail below
    (Supplementary Tables 1 and 3 give detailed statistics for each
    session individually; Supplementary Fig. 1 and Supplementary
    Table 2 summarize the effects for each patch)."

    "We chose AM since it is the
    most anterior, high-level patch in the system, based on both functional
    and anatomical criteria3,23. Therefore, if any patch would be expected
    to code purely faces and not other objects, it would be AM."

    As our methods find the center of the model face patch perfectly, we are working with the values
    from the sessions with the maximum effects.
    From Lee et al. 2020 we make the assumption that out in silico face patch is equivalent to AM.

    :return: dictionary with keys:
                accuracies          = list, accuracy computed w.r.t. rest of keys
                condition           = list, {same, different}_id
                current_pulse_mA    = list, {0, 300}
                object_name         = list, category name
                source              = list, monkey number
    """
    # statistic for each dataset
    path = Path(__file__).parent / 'SummaryMat.xlsx'
    df = pd.read_excel(path)

    # select relevant lines
    df = df.loc[(df.Stimulus_Class == stimulus_class) &
                (df.Perturbation_Location == perturbation_location)]

    # compute accuracies
    data = {'accuracies': [], 'condition': [], 'current_pulse_mA': [], 'object_name': [], 'subject': []}
    for condition, stimulation in itertools.product(['Same', 'Different'], ['', '_MSC']):
        setup = condition + stimulation
        accuracy = df['Hit_' + setup] / (df['Hit_' + setup] + df['Miss_' + setup])
        data['accuracies'] += accuracy.to_list()
        data['condition'] += [condition.lower() + '_id'] * len(accuracy)
        data['current_pulse_mA'] += [300] * len(accuracy) if stimulation == '_MSC' else [0] * len(accuracy)
        data['object_name'] += df.Object_Names.to_list()
        data['subject'] += df.Monkey.to_list()

    return pd.DataFrame(data)


def _load_stimulus_set(stimulus_class):
    """
    Load stimuli as specified by the paper; relevant parameter: self._stimulus_class

    :return: StimulusSet object containing information about image path, object class and object identity
    """
    path = Path(__file__).parent / stimulus_class
    stimulus_ids = listdir(path)
    object_names, object_ids = [], []
    for stimulus_id in stimulus_ids:
        object_ids.append(re.split(r"_", stimulus_id)[1])
        if stimulus_class == 'Objects':
            object_names.append('object')
        elif stimulus_class == 'Faces' or ''.join([c for c in object_ids[-1] if not c.isdigit()]) == 'r':
            object_names.append('face')
        else:
            object_names.append(''.join([c for c in object_ids[-1] if not c.isdigit()]))
    stimulus_set = StimulusSet({'stimulus_id': stimulus_ids, 'object_name': object_names, 'object_id': object_ids})
    stimulus_set.identifier = 'Moeller2017-' + stimulus_class
    stimulus_set.stimulus_paths = {id: str(path / id) for id in stimulus_ids}
    return stimulus_set


def _load_training_stimuli():
    """
    From Online Methods section. Behavioral training section: [...]
    "Next, we trained animals on the main task (32 faces, 6 exemplars each).
    Image selection was exactly as in the second training task except that in the sameidentity condition we
    drew the second cue from all six images of the selected
    identity. Both animals showed stable, good performance on this task across many
    sessions (Supplementary Fig. 11c,d).

    Finally, we presented stimulus sets consisting of non-face objects (either
    16, 19 or 28 objects; see Experiment 2). For this task, both animals immediately began performing at
    >70% correct, indicating that they could generalize
    the same/different identification task independent of the actual stimuli presented
    (Supplementary Fig. 11e,f). The same generalization was evident in
    the round object identification task (see Experiment 3 and Supplementary
    Fig. 11g,h; for the abstracted faces and houses from Experiment 4b,
    see Supplementary Fig. 11i,j)."

    We simplify all of this to just training on faces directly, and ignore the basic training for paradigm etc. before.

    :return: StimulusSet Object, same as 'Faces' used in Experiment 1
    """
    stimulus_class = 'Faces'
    path = Path(__file__).parent / stimulus_class
    stimulus_ids = listdir(path)
    object_names, object_ids = [], []
    for stimulus_id in stimulus_ids:
        object_ids.append(re.split(r"_", stimulus_id)[1])
        object_names.append('face')
    stimuli = StimulusSet({'stimulus_id': stimulus_ids, 'object_name': object_names, 'object_id': object_ids})
    stimuli.identifier = 'Moeller2017-Faces'
    stimuli.stimulus_paths = {id: str(path / id) for id in stimulus_ids}
    return stimuli


def _load_stimulus_set_face_patch():
    """
    From Online Methods, Face patch localization section:
    "Two male rhesus macaques were trained to maintain
    fixation on a small spot for juice reward. Monkeys were scanned in a 3T TIM Trio
    (Siemens) magnet equipped with an AC88 gradient insert while passively viewing images on a screen.
    MION contrast agent (8 mg/kg body weight, Feraheme, AMAG) was injected to improve signal to noise ratio. [...]"

    I assume just use some images for face patch localization

    :return: StimulusSet object, hvm images
    """
    return brainscore_vision.load_stimulus_set('dicarlo.hvm')