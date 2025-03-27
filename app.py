from flask import Flask, render_template, request, send_file
from piano_transcription_inference import PianoTranscription, sample_rate, load_audio
import os
import subprocess
from music21 import stream, note, converter

app = Flask(__name__)
app.secret_key = 'SurShastra'
download_folder = './downloads'
os.makedirs(download_folder, exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file-upload']
        if file.filename != '':
            file_path = os.path.join(download_folder, 'uploaded.mp3')
            file.save(file_path)
            (audio, _) = load_audio(file_path, sr=sample_rate, mono=True)
            transcriptor = PianoTranscription(device='cpu')
            midi_file_path = os.path.join(download_folder, 'transcribed.mid')
            transcriptor.transcribe(audio, midi_file_path)

            # Load MIDI into music21 and extract notes
            midi_score = converter.parse(midi_file_path)
            note_info = []
            for part in midi_score.parts:
                for element in part.flat.notes:
                    if isinstance(element, note.Note) or isinstance(element, note.Rest):
                        note_info.append(element)

            # Generate additional files
            s = stream.Score()
            notes_file_path = os.path.join(download_folder, 'notes.txt')
            with open(notes_file_path, 'w') as file:
                for n in note_info:
                    if isinstance(n, note.Note):
                        pitch = n.nameWithOctave
                    else:
                        pitch = 'Rest'
                    s.append(n)
                    file.write(f"{pitch}\n")

            s.write('musicxml', fp=os.path.join(download_folder, 'song.xml'))
            print("MusicXML file 'song.xml' generated successfully.")
            
            # notes_file_path = os.path.join(download_folder, 'notes.txt')
            # with open(notes_file_path, 'w') as file:
            #     for note in note_info:
            #         if isinstance(note, list):
            #             file.write(f"{note[0].nameWithOctave}\n")
            #         else:
            #             file.write(f"{note.name}\n")
            
            # Generate PDF using MuseScore
            command = ['C:/Program Files/MuseScore 4/bin/MuseScore4.exe', '-o', 'sheet.pdf', 'song.xml']
            subprocess.run(command, cwd=download_folder)
    
            return render_template('download.html')
    
    return render_template('index.html')

@app.route('/recording_mid')
def download_midi():
    return send_file(os.path.join(download_folder, 'transcribed.mid'), as_attachment=True)

@app.route('/notes_txt')
def notes_txt():
    notes_file_path = './downloads/notes.txt'
    return send_file(notes_file_path, as_attachment=True)

@app.route('/song_xml')
def song_xml():
    xml_file_path = './downloads/song.xml'
    return send_file(xml_file_path, as_attachment=True)

@app.route('/sheet_pdf')
def sheet_pdf():
    pdf_file_path = './downloads/sheet.pdf'
    return send_file(pdf_file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
