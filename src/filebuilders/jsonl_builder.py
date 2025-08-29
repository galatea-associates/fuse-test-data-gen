from filebuilders.file_builder import FileBuilder
import ujson
import os


class JSONLBuilder(FileBuilder):
    """ A class to generate a JSONL file from records. JSONL is JSON but each
    object appears on a new and single line. The ujson library used to format
    data into JSON format, and these are joined with a new line. """

    def build(self, file_number, data):
        output_dir = self.get_output_directory()
        file_name = self.get_file_name().format(f'{file_number:03}')

        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        with open(os.path.join(output_dir, file_name), 'w') as output_file:
            to_output = [ujson.dumps(record) for record in data]
            formatted_output = "\n".join(to_output)
            output_file.write(formatted_output)

        if self.google_drive_connector_exists():
            self.upload_to_google_drive(output_dir, file_name)
