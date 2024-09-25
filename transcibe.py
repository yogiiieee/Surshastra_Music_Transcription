import globals as g
import librosa
import numpy as np
from music21.tempo import MetronomeMark
from music21.note import Note, Rest
from music21.stream import Stream
from music21 import metadata, instrument
import subprocess

# Calculate Constant-Q Transform and return its magnitude in dB
def calculate_cqt(x, fs):
    cqt = librosa.cqt(x, sr=fs, hop_length=g.hop_length, fmin=None, n_bins=g.n_bins)
    cqt_mag = librosa.magphase(cqt)[0]**g.mag_exp
    cqt_dB = librosa.core.amplitude_to_db(cqt_mag, ref=np.max)
    return cqt_dB

# Apply threshold to CQT magnitude
def cqt_threshold(cqt):
    copy_cqt = np.copy(cqt)
    copy_cqt[copy_cqt < g.cqt_threshold] = -120
    return copy_cqt

# Calculate onset envelope
def calculate_onset_envelope(cqt, fs):
    return librosa.onset.onset_strength(S=cqt, sr=fs,aggregate=np.mean, hop_length=g.hop_length)

# Detect onsets from onset envelope
def calculate_onset(cqt, fs, backtrack = True):
    onset_envelope = calculate_onset_envelope(cqt, fs)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_envelope,
                                              sr=fs,
                                              units='frames',
                                              hop_length=g.hop_length,
                                              backtrack=backtrack,
                                              pre_max=g.pre_post_max,
                                              post_max=g.pre_post_max)
    onset_boundaries = np.concatenate([[0], onset_frames, [cqt.shape[1]]])
    onset_times = librosa.frames_to_time(onset_boundaries, sr=fs, hop_length=g.hop_length)
    return [onset_times, onset_boundaries, onset_envelope]

# Convert time duration to beats
def time_to_beat(duration, tempo):
    return (tempo*duration/60)

# Remap a value from one range to another
# This function is used to scale amplitude from the range of decibel values in cqt_dB to the range of 0 to 1.
def remap(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

# Generate sine wave MIDI notes
def generate_sine_midi_note(f0_info, fs, n_duration, tempo, cqt_dB, metronome_mark, round_to_sixteenth=True):
    f0 = f0_info[0]
    amplitude = remap(f0_info[1], cqt_dB.min(), cqt_dB.max(), 0, 1)
    duration = librosa.frames_to_time(n_duration, sr=fs, hop_length=g.hop_length)
    note_duration = 0.02*np.around(duration/2/0.02)
    midi_duration = time_to_beat(duration, tempo)
    midi_velocity = int(round(remap(f0_info[1], cqt_dB.min(), cqt_dB.max(), 0, 127)))
    metronome_mark_type = metronome_mark.secondsToDuration(note_duration).type
    if round_to_sixteenth:
        midi_duration = round(midi_duration*16)/16
    if f0 == None:
        midi_note = None
        note = Rest(type='quarter')
        if metronome_mark_type != 'inexpressible':
            note_info = Rest(type=metronome_mark_type)
        else:
            note_info = Rest(type='quarter')
        # note_info = Rest(type='quarter')
        f0 = 0
    else:
        # midi_note = round(librosa.hz_to_midi(f0))
        # if metronome_mark_type != 'inexpressible':
        #     note = Note(librosa.midi_to_note(midi_note).replace('♯','#'), type=metronome_mark_type)
        # else:
        #     note = Note(librosa.midi_to_note(midi_note).replace('♯','#'), type='quarter')
        #     note.duration.dots = 2
        # note = Note(librosa.midi_to_note(midi_note).replace('♯','#'), type='quarter')
        # note.volume.velocity = midi_velocity
        midi_note = round(librosa.hz_to_midi(f0))
        if metronome_mark_type != 'inexpressible':
            if metronome_mark_type in ['12th', 'sixteenth', '32nd', '64th']:
                metronome_mark_type = 'eighth'
            note = Note(librosa.midi_to_note(midi_note).replace('♯','#'), type=metronome_mark_type)
            # note.duration.dots = 1
        else:
            note = Note(librosa.midi_to_note(midi_note).replace('♯','#'), type='quarter')
            # note.duration.dots = 1
            note.duration.dots = 2
        note.volume.velocity = midi_velocity
        note_info = [note]
    midi_info = [midi_note, midi_duration, midi_velocity]
    # Generate sinewave
    n = np.arange(librosa.frames_to_samples(n_duration, hop_length=g.hop_length))
    sine_wave = amplitude*np.sin(2*np.pi*f0*n/float(fs))
    return [sine_wave, midi_info, note_info]

# Estimate pitch
def estimate_pitch(segment, threshold):
    freqs = librosa.cqt_frequencies(n_bins=g.n_bins, fmin=librosa.note_to_hz('C1'),
                                    bins_per_octave=12)
    if segment.max() < threshold:
        return [None, np.mean((np.amax(segment, axis=0)))]
    else:
        f0 = int(np.mean((np.argmax(segment, axis=0))))
    return [freqs[f0], np.mean((np.amax(segment, axis=0)))]

def estimate_pitch_and_notes(x, onset_boundaries, i, fs, tempo, cqt_dB, metronome_mark):
    n0 = onset_boundaries[i]
    n1 = onset_boundaries[i+1]
    f0_info = estimate_pitch(np.mean(x[:, n0:n1], axis=1), threshold=g.cqt_threshold)
    return generate_sine_midi_note(f0_info, fs, n1-n0, tempo, cqt_dB, metronome_mark)

def increase_volume(stream_obj, velocity_increase=20):
    for note in stream_obj.flat.notes:
        if note.volume.velocity is not None:
            note.volume.velocity = min(note.volume.velocity + velocity_increase, 127)

def main():
    filename = 'file.wav'
    x, fs = librosa.load(filename, sr=None, mono=True)
    cqt_dB = calculate_cqt(x, fs)
    cqt = cqt_threshold(cqt_dB)
    onsets = calculate_onset(cqt, fs, backtrack=False)

    tempo, beats = librosa.beat.beat_track(y=None, sr=fs, onset_envelope=onsets[2], hop_length=g.hop_length,
                                           tightness=100, trim=True, bpm=None, units='frames')
    print(tempo)
    if isinstance(tempo, np.ndarray):
        tempo = tempo.item()
    tempo = int(2*round(tempo/2))
    metronome_mark = MetronomeMark(referent='quarter', number=tempo)

    # Estimate pitch and generate MIDI notes for each onset segment
    notes=[]
    for i in range(len(onsets[1])-1):
        notes.append(estimate_pitch_and_notes(cqt, onsets[1], i, fs, tempo, cqt_dB, metronome_mark))
    music_info = np.array(notes, dtype=object)

    # Get sinewave
    sine_wave_audio = np.concatenate(music_info[:, 0])
    # Get music21 notes
    note_info = list(music_info[:, 2])
    if(note_info[0] == Rest(type='breve')):
        note_info[0] = Rest(type='half')
    # Create music21 stream
    s = Stream()
    s.append(metronome_mark)
    instrumentt = instrument.fromString('piano')
    # instrumentt = instrument.fromString('electric guitar')
    # piano.midiChannel = 0
    # piano.midiProgram = 30
    s.append(instrumentt)
    s.insert(0, metadata.Metadata())
    s.metadata.title = 'Music Sheet'
    s.metadata.composer = 'Surshastra'
    for notes in note_info:
        s.append(notes)
    key = s.analyze('key')
    s.insert(0, key)
    increase_volume(s)
    s.write('musicxml', fp='downloads/song.xml')
    print(f"MusicXML file 'song.xml' generated successfully.")
    s.write('midi', fp='downloads/recording.mid')
    print(f"MusicXML file 'recording.mid' generated successfully.")
    with open('downloads/notes.txt', 'w') as file:
        for note in note_info:
            if isinstance(note, list):
                file.write(f"{note[0].nameWithOctave}\n")
            else:
                file.write(f"{note.name}\n")
    
    path = './downloads'
    command = ['C:/Program Files/MuseScore 4/bin/MuseScore4.exe', '-o', 'sheet.pdf', 'song.xml']
    subprocess.run(command, cwd=path)

if __name__ == '__main__':
    main()