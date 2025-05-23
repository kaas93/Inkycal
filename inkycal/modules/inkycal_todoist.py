"""
Inkycal Todoist Module
Copyright by aceinnolab
"""
import arrow

from inkycal.modules.template import inkycal_module
from inkycal.custom import *

from todoist_api_python.api import TodoistAPI

logger = logging.getLogger(__name__)


class Todoist(inkycal_module):
    """Todoist api class
    parses todos from the todoist api.
    """

    name = "Todoist API - show your todos from todoist"

    requires = {
        'api_key': {
            "label": "Please enter your Todoist API-key",
        },
    }

    optional = {
        'project_filter': {
            "label": "Show Todos only from following project (separated by a comma). Leave empty to show " +
                     "todos from all projects",
        }
    }

    def __init__(self, config):
        """Initialize inkycal_rss module"""

        super().__init__(config)

        config = config['config']

        # Check if all required parameters are present
        for param in self.requires:
            if param not in config:
                raise Exception(f'config is missing {param}')

        # module specific parameters
        self.api_key = config['api_key']

        # if project filter is set, initialize it
        if config['project_filter'] and isinstance(config['project_filter'], str):
            self.project_filter = config['project_filter'].split(',')
        else:
            self.project_filter = config['project_filter']

        self._api = TodoistAPI(config['api_key'])

        # give an OK message
        logger.debug(f'{__name__} loaded')

    def _validate(self):
        """Validate module-specific parameters"""
        if not isinstance(self.api_key, str):
            print('api_key has to be a string: "Yourtopsecretkey123" ')

    def generate_image(self):
        """Generate image for this module"""

        # Define new image size with respect to padding
        im_width = int(self.width - (2 * self.padding_left))
        im_height = int(self.height - (2 * self.padding_top))
        im_size = im_width, im_height
        logger.debug(f'Image size: {im_size}')

        # Create an image for black pixels and one for coloured pixels
        im_black = Image.new('RGB', size=im_size, color='white')
        im_colour = Image.new('RGB', size=im_size, color='white')

        # Check if internet is available
        if internet_available():
            logger.info('Connection test passed')
        else:
            logger.error("Network not reachable. Please check your connection.")
            raise NetworkNotReachableError

        # Set some parameters for formatting todos
        line_spacing = 1
        text_bbox_height = self.font.getbbox("hg")[3]
        line_height = text_bbox_height + line_spacing + 3
        max_lines = (im_height - self.fontsize - 12)// line_height

        # Calculate padding from top so the lines look centralised
        corrective_spacing = int(im_height % line_height / 2)
        spacing_top = self.fontsize + 16 + corrective_spacing

        # Calculate line_positions
        line_positions = [
            (0, spacing_top + _ * line_height) for _ in range(max_lines)]

        # Get all projects by name and id
        all_projects = self._api.get_projects()
        filtered_project_ids_and_names = {project.id: project.name for project in all_projects}
        all_active_tasks = self._api.get_tasks()

        logger.debug(f"all_projects: {all_projects}")

        # Filter entries in all_projects if filter was given
        if self.project_filter:
            filtered_projects = [project for project in all_projects if project.name in self.project_filter]
            filtered_project_ids_and_names = {project.id: project.name for project in filtered_projects}
            filtered_project_ids = [project for project in filtered_project_ids_and_names]
            logger.debug(f"filtered projects: {filtered_projects}")

            # If filter was activated and no project was found with that name,
            # raise an exception to avoid showing a blank image
            if not filtered_projects:
                logger.error('No project found from project filter!')
                logger.error('Please double check spellings in project_filter')
                raise Exception('No matching project found in filter. Please '
                                'double check spellings in project_filter or leave'
                                'empty')
            # filtered version of all active tasks
            all_active_tasks = [task for task in all_active_tasks if task.project_id in filtered_project_ids and (task.due and task.due.date)]
            section_names_by_id = {section_id: self._api.get_section(section_id).name for section_id in [task.section_id for task in all_active_tasks]}

        # Simplify the tasks for faster processing
        simplified = [
            {
                'name': task.content,
                'due': "[" + arrow.get(task.due.date, "YYYY-MM-DD").format("DD-MM-YY") + "]",
                'priority': task.priority,
                'section': section_names_by_id[task.section_id],
                'project': filtered_project_ids_and_names[task.project_id]
            }
            for task in sorted(all_active_tasks, key=lambda x: x.due.date)
        ]

        logger.debug(f'simplified: {simplified}')

        section_lengths = []
        due_lengths = []

        for task in simplified:
            if task["section"]:
                section_lengths.append(int(self.font.getlength(task['section']) * 1.1))
            if task["due"]:
                due_lengths.append(int(self.font.getlength(task['due']) * 0.95))

        # Get maximum width of project dues for selected font
        due_offset = int(max(due_lengths)) if due_lengths else 0

        # create a dict with names of filtered groups
        groups = {group_name:[] for group_name in filtered_project_ids_and_names.values()}
        for task in simplified:
            group_of_current_task = task["project"]
            if group_of_current_task in groups:
                groups[group_of_current_task].append(task)

        logger.debug(f"grouped: {groups}")

        write(
            im_black,
            (0, 0),
            (im_width, line_height - 2),
            "Upcoming Events", font=ImageFont.truetype(fonts['NotoSansUI-Bold'], self.fontsize + 2), alignment='center')

        draw_line(
            im_colour, 
            (0, line_height + 2),
            (im_width, line_height + 2),
            4
        )

        # Add the parsed todos on the image
        cursor = 0
        for name, todos in groups.items():
            if not todos: continue
            for todo in todos:
                if cursor < max_lines:
                    line_x, line_y = line_positions[cursor]

                    if todo['section']:
                        draw_avatar(im_black,
                                    im_colour,
                                    (line_x, line_y + 3),
                                    (line_height - 3, line_height - 3),
                                    todo['section'],
                                    font=ImageFont.truetype(fonts['NotoSansUI-Bold'], self.fontsize - 3))

                    write(
                        im_black,
                        (line_x + line_height + 1, line_y),
                        (due_offset, line_height),
                        todo['due'], font=ImageFont.truetype(self.font.path, self.fontsize - 2), alignment='left')

                    if todo['name']:
                        # Add todos name
                        write(
                            im_black,
                            (line_x + line_height + due_offset, line_y),
                            (im_width - line_height - due_offset, line_height),
                            todo['name'], font=self.font, alignment='left')

                    cursor += 1
                else:
                    logger.error('More todos than available lines')
                    break

        # return the images ready for the display
        return im_black, im_colour
