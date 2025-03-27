from flask import Flask, render_template, request, send_file
from piano_transcription_inference import PianoTranscription, sample_rate, load_audio
import os
import subprocess
from music21 import stream, note, converter, chord
from tabulate import tabulate

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

            # Process MIDI file
            midi_score = converter.parse(midi_file_path)
            full_score = stream.Score()
            
            # Prepare data for tabulate
            table_data = []
            headers = ["Note", "Start", "Duration", "Octave", "Type"]
            
            for part in midi_score.parts:
                new_part = stream.Part()
                for element in part.flat.notesAndRests:
                    new_part.append(element)
                    
                    # Extract note information
                    if isinstance(element, note.Note):
                        row = [
                            element.pitch.name,
                            element.offset,
                            element.duration.quarterLength,
                            element.pitch.octave,
                            "Note"
                        ]
                    elif isinstance(element, chord.Chord):
                        row = [
                            '.'.join(p.nameWithOctave for p in element.pitches),
                            element.offset,
                            element.duration.quarterLength,
                            '-',
                            "Chord"
                        ]
                    elif isinstance(element, note.Rest):
                        row = [
                            "Rest",
                            element.offset,
                            element.duration.quarterLength,
                            '-',
                            "Rest"
                        ]
                    table_data.append(row)
                    
                full_score.append(new_part)
            
            # Generate notes file with tabulate
            notes_file_path = os.path.join(download_folder, 'notes.txt')
            with open(notes_file_path, 'w') as f:
                # Create formatted table
                formatted_table = tabulate(
                    table_data, 
                    headers=headers, 
                    tablefmt="grid",  
                    floatfmt=".2f" 
                )
                f.write("Extracted Notes Information:\n\n")
                f.write(formatted_table)
                f.write("\n\n=== Additional Information ===\n")
                f.write(f"Total notes: {len(table_data)}\n")
                f.write(f"Time signature: {midi_score.flat.getTimeSignatures()[0] if midi_score.flat.getTimeSignatures() else 'Not specified'}\n")
                f.write(f"Key signature: {midi_score.flat.getKeySignatures()[0] if midi_score.flat.getKeySignatures() else 'Not specified'}\n")
            
            # Generate MusicXML and PDF
            musicxml_path = os.path.join(download_folder, 'sheet.xml')
            full_score.write('musicxml', fp=musicxml_path)
            
            command = ['C:/Program Files/MuseScore 4/bin/MuseScore4.exe', '-o', 'sheet.pdf', 'sheet.xml']
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
