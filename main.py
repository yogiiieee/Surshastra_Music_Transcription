from flask import Flask, render_template, request, send_file
import transcibe

app = Flask(__name__)
app.secret_key = 'Surshastra'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file-upload']
        if file.filename != '':
            file.save('file.wav')
            transcibe.main()
            return render_template('download.html')
    return '<h1>An unexpected error occured.</h1>'

@app.route('/recording_mid')
def recording_mid():
    midi_file_path = './downloads/recording.mid'
    return send_file(midi_file_path, as_attachment=True)

@app.route('/sheet_pdf')
def sheet_pdf():
    pdf_file_path = './downloads/sheet.pdf'
    return send_file(pdf_file_path, as_attachment=True)

@app.route('/notes_txt')
def notes_txt():
    notes_file_path = './downloads/notes.txt'
    return send_file(notes_file_path, as_attachment=True)

@app.route('/song_xml')
def song_xml():
    xml_file_path = './downloads/song.xml'
    return send_file(xml_file_path, as_attachment=True)

if __name__ == '__main__':
    app.run()