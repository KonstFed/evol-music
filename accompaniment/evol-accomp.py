import random
import re
import argparse
import warnings
from mido import MidiFile, Message, tempo2bpm, MidiTrack, open_output

import music21

try:
    from tqdm import trange
except ImportError:
    warnings.warn("tqdm is not found. Fancy progress bars can not be used")
    trange = range

try:
    import matplotlib.pyplot as plt

    MATPLOTLIB_OK = True
except ImportError:
    warnings.warn("matplotlib is not found. Statistic graphical output of evolution algorithm can not be used")
    MATPLOTLIB_OK = False

chords_matrix_major = [
    [0, 2, 3],
    [1, 2, 3],
    [1, 3],
    [0, 2],
    [0, 2, 3],
    [1, 2, 3],
    [4]
]

chords_matrix_minor = [
    [1, 2, 3],
    [4],
    [0, 2, 3],
    [1, 2, 3],
    [1, 3],
    [0, 2],
    [0, 2, 3],
]

existingTriads = [
    [0, 4, 7],
    [0, 3, 7],
    [0, 2, 7],
    [0, 5, 7],
    [0, 3, 6]
]

basic_chords_progressions = [
    "1455",
    "1145",
    "1415",
    "1454"
]


def midiNote(note, time=0, velocity=30):
    """
    Creates mido message of type "note_on"
    """
    return Message('note_on', note=note, time=time, velocity=velocity)


def midiNoteOff(note, time=0, velocity=30):
    """
    Creates mido message of type "note_off"
    """
    return Message('note_off', note=note, time=time, velocity=velocity)


def get_midi_chord(scale, chord, triad, chord_time):
    """
    Transforms chord to mido messages
    """
    midis = []
    for i in range(len(triad)):
        midis.append(midiNote(scale[chord] + triad[i] - 24))
    midis.append(midiNoteOff(scale[chord] + triad[0] - 24, chord_time))
    for i in range(1, len(triad)):
        midis.append(midiNoteOff(scale[chord] + triad[i] - 24))
    return midis


def get_midi_chromosome(key, chromosome, chord_time):
    """
    Transform chromosome to mido messages
    """
    scale = []
    for pitch in key.getScale(key.mode).pitches:
        scale.append(pitch.midi)
    midis = []
    for chord, triad in chromosome:
        midis = midis + get_midi_chord(scale, chord, triad, chord_time)
    return midis


def add_accompaniment(original, key, chromosome, chord_time):
    """
    returns chromosome added to original melody in .mid format
    """
    track = MidiTrack()
    midis = get_midi_chromosome(key, chromosome, chord_time)
    track = track + midis
    original.type = 1
    original.tracks.append(track)
    return original


def generate_gene(mode):
    """
    Generate random gene. returns tuple of scale offset and triad of chord.
    """
    note = random.randint(0, 6)
    type = random.choice(chords_matrix_major[note]) if mode == "major" else random.choice(chords_matrix_minor[note])
    return note, tuple(existingTriads[type])


def generate_chromosome(n, mode):
    """
    Generate random chromosome of size n.
    """
    genes = []
    for i in range(n):
        genes.append(generate_gene(mode))
    return genes


def get_temp(mid):
    """
    Get temp from .mid file
    """
    temp = 500000
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                temp = msg.tempo
                break
    return temp


def get_n_chords(mid):
    """
    Get number of chords needed to be played
    """
    return int(mid.length * 10 ** 6 // get_temp(mid))


def mutate(mode, chromosome, mutation_probability):
    """
    Mutate given chromosome.
    1 gene will mutate anyway.
    Others will mutate with probability 'mutation_probability'
    """
    mutant = chromosome.copy()
    i = random.randint(0, len(mutant) - 1)
    mutant[i] = generate_gene(mode)
    for j in range(len(mutant)):
        if i == j:
            continue
        elif random.random() < mutation_probability:
            mutant[j] = generate_gene(mode)
    return mutant


def cross(father, mother):
    """
    Cross two chromosomes. Returns two children chromosomes.
    2 indexes are chosen at random: left and right.

    1st child is composed as follows: father[:l+1] + mother[l+1:r] + father[r:].

    2st child is composed as follows: mother[:l+1] + father[l+1:r] + mother[r:].
    """
    l = random.randint(0, len(father) - 1)
    if l == len(father) - 1:
        return [father.copy(), mother.copy()]
    r = random.randint(l + 1, len(father) - 1)
    return [father[:l + 1] + mother[l + 1:r] + father[r:], mother[:l + 1] + father[l + 1:r] + mother[r:]]


def get_notes_interval(midi, n):
    """
    Computes list of notes of size n.
    It represents which notes from melody where played during every chord.
    """
    notes_interval = {}
    ticks = 0
    for track in midi.tracks:
        for msg in track:
            ticks += msg.time
            if msg.type == "note_on":
                if msg.note not in notes_interval:
                    notes_interval[msg.note] = []
                notes_interval[msg.note].append([ticks / midi.ticks_per_beat, -1])
            elif msg.type == "note_off":
                notes_interval[msg.note][-1][1] = ticks / midi.ticks_per_beat
    notes_per_chord = []
    for i in range(n):
        notes_per_chord.append([])
        for note in notes_interval:
            for j in notes_interval[note]:
                if j[0] <= i < j[1]:
                    notes_per_chord[i].append(note)
                    break
    return notes_per_chord


def find_sequence(sequence: str, desired: str):
    """
    finds number of occurrences in sequence
    """
    return len(re.findall(desired, sequence))


major_offsets = [0, 2, 4, 5, 7, 9, 11]
minor_offsets = [0, 2, 3, 5, 7, 8, 10]


def fitness_notes_coincidence(chromosome, mode, notes_interval, tonic):
    """
    Returns fitness score based on note coincidence from melody and chords.
    If note present in a melody and respective chord doesn't contain it, it will decrease score by 10.
    Overall score is divided by number of chords
    """
    notes_match = 0
    n_melody_notes = 0
    for i in range(len(chromosome)):
        if mode == "major":
            scale = major_offsets
        else:
            scale = minor_offsets
        rim, triad = chromosome[i]
        chord_note = [scale[rim] + tonic + x for x in triad]
        for melody_note in notes_interval[i]:
            n_melody_notes += 1
            if melody_note not in chord_note:
                notes_match -= 10

    f = notes_match / n_melody_notes
    return f


def fitness_chord_progression(chromosome):
    """
    Returns fitness score based on chord progressions presence.
    It counts number of chord progressions detected in chromosome and then divide it by number of chords.
    """
    chords = ""
    for note, chord_type in chromosome:
        if chord_type[0] == 0 and (chord_type[1] == 3 or chord_type[1] == 4) and chord_type[2] == 7:
            chords += str(note + 1)
        else:
            chords += "0"
    n_three_chord_progressions = 0
    for chords_progression in basic_chords_progressions:
        n_three_chord_progressions += find_sequence(chords, chords_progression)
    ratio = n_three_chord_progressions / len(chords)
    return ratio


def fitness(chromosome, mode, notes_interval, tonic, log=False):
    """
    Returns fitness score based on two other fitness function: fitness_notes_coincidence and fitness_chord_progression.

    log = True, will print to stdout values of each fitness function separately.
    """
    f_coind = fitness_notes_coincidence(chromosome, mode, notes_interval, tonic)
    f_progression = fitness_chord_progression(chromosome)
    if log:
        print("Note coincidence:", f_coind)
        print("Progression chord: ", f_progression)
    return f_coind + f_progression


def evolution_step(mode, population, notes_interval, tonic, mutation_probability, population_size, cross_size):
    """
    performs one step of evolution algorithm.
    """
    for i in range(cross_size):
        a, b = cross(population[2 * i], population[2 * i + 1])
        a = mutate(mode, a, mutation_probability)
        b = mutate(mode, b, mutation_probability)
        population.append(a)
        population.append(b)
    for i in range(population_size):
        mutant = mutate(mode, population[i], mutation_probability)
        population.append(mutant)
    population.sort(key=lambda x: fitness(x, mode, notes_interval, tonic), reverse=True)
    population = population[:population_size]
    return population


def evolution(n, key, original, iterations=1000, population_size=100, cross_size=50, return_statistics=False):
    """
    Perform evolutionary algorithm.
    """
    notes_interval = get_notes_interval(original, n)
    population = []
    mode = key.mode
    tonic = key.tonic.midi
    mutation_probability = 0.2
    if return_statistics:
        bests = []
    for i in range(population_size):
        population.append(generate_chromosome(n, key))
    for i in trange(iterations):
        population = evolution_step(mode, population, notes_interval, tonic, mutation_probability, population_size,
                                    cross_size)
        if return_statistics:
            bests.append(fitness(population[0], mode, notes_interval, tonic))
    if return_statistics:
        return population[0], bests
    else:
        return population[0]


def compose(path, output_path=None, graph_mode=False):
    """
    will create accompaniment to a given mid file.
    Will save in a "KonstantinFedorovInput1" format if parameter n is given.
    """
    song = MidiFile(path)
    key = music21.converter.parse(path).analyze('key')
    n = get_n_chords(song)
    best = evolution(n, key, song, iterations=300, population_size=200, return_statistics=graph_mode)
    if graph_mode:
        best, statistics = best
        plt.plot(statistics)
        plt.show()
    song = add_accompaniment(song, key, best, song.ticks_per_beat)
    if output_path is not None:
        song.save(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='evol-accomp',
        description='This program generates accompaniment for melody given in .mid format',
        epilog='')
    parser.add_argument('-s', '--save', action="store", help='save program to given path')
    parser.add_argument('-p', '--plot', action="store_true", help='save program to given path')
    parser.add_argument('path', help='path to melody in .mid format')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.1')
    args = parser.parse_args()
    if args.save:
        compose(args.path, output_path=args.save, graph_mode=args.plot)
    else:
        compose(args.path, graph_mode=args.plot)
