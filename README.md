# Accompaniment Generation
Author: Konstantin Fedorov

# Dependencies

## Necessary

- [mido](https://mido.readthedocs.io/en/latest/)
- [music21](https://github.com/cuthbertLab/music21)

## Optional

- [tqdm](https://github.com/tqdm/tqdm)
- [matplotlib](https://matplotlib.org)

# Launch guide
In order to launch code you should use this command:

If you want generate you should type like this:
```console
python3 evol-accomp.py input.mid --save some_path/file2.mid
```
You can also plot fitness function score through generations
```console
python3 --plot evol-accomp.py input.mid --save some_path/file2.mid
```
For more information write
```console
python3 evol-accomp.py --help
```
# Algorithm

## Constraints

Accompaniment generates only:
- for songs that have 1 midi track.
- for songs with not changing tempo
- for songs with constant key
- for songs with natural major and natural minor keys

## Key detection algorithm
Key consist of two parameters: tonic and mode.
Also we can retrieve scale: notes that we can play in this key.

Key detection is based on `music21` standart key detection algorithm

## Detected keys for inputs

- input1.mid is D minor
- input2.mid is F major
- input3.mid is E minor

## Chord generation
Chord can be represented as scale step based on key and chord type. We consider following chord types:
- Major
- Minor
- SUS2
- SUS4
- Diminished

Inverses of major and minor are not used in my implementation because they usually sound unpleasant and expand search space without significant benefit.

7 scale step exist for any key. But not all type of chords can be played with any scale step and key mode.

For major key we choose following chords type:

- 1 step: Major, SUS2, SUS4
- 2 step: Minor, SUS2, SUS4
- 3 step: Minor, SUS4
- 4 step: Major, SUS2
- 5 step: Major, SUS2, SUS4
- 6 step: Minor, SUS2, SUS4
- 7 step: Diminished

For minor key we choose following chords type:

- 1 step: Minor, SUS2, SUS4
- 2 step: Diminished
- 3 step: Major, SUS2, SUS4
- 4 step: Minor, SUS2, SUS4
- 5 step: Minor, SUS4
- 6 step: Major, SUS2
- 7 step: Major SU
  
Any other combinations are considered as unpleasant.

Every chord plays midi.ticks_per_beat time.

## Evolutionary algorithm

In order to use algorithm we compute needed number of chords:

```python
n_chords = seconds * 10**6 // temp
```
We can get temp from midi file meta message.

### Chromosome

Chromosome consist of `n_chords` genes. Each gene is chord. 

Mutation algorithm:
- Choose one random gene and change it
- For every other gene mutatute with probability `0.2`

Cross performs between 2 chromosomes: father and mother. It will return 2 child chromosomes. 

Algorithm:
- 1st child is composed as follows: from 0 chord to left index and from right index to the last chord inclusively from father; from left to right index inclusively from mother. Could be written in python manner as: `father[:l+1] + mother[l+1:r] + father[r:]`
- 2nd child is similar to 1st, but instead of father we take genes from mother and vice versa.

### Fitness function

Fitness function can be split to two components:
- Note coincidence 
- Chord progressions

We compute note coincidence score as follows: for every note in melody: if respective chord doesn't contain this note, we subtract 10 from score. Then we divide by number of notes in melody.

For chord progressions we write our chromosome as string where every character is scale step of gene. However, if chord is not major or minor we write `'0'` instead. Then we try find following sequences in the string:

- 1455
- 1145
- 1415
- 1454

Then we count number of matches and divide by number of chords.

Final fitness score is calculated as sum of note coincidence and chord progressions score.

### Selection process

Firstly we generate randomly 200 chromosomes. 
Then we repeat following algorithm 300 times:

- Cross 50 pairs of best chromosomes and mutate them
- Mutate all population chromosomes
- Add to population cross and mutation result
- Sort it by fitness function
- Take 200 best as population

After that we choose best chromosome as our accompaniment.
