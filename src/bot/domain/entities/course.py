from pydantic import BaseModel

from bot.domain.entities.mappings import StudyCourses, StudyGroups


class Course(BaseModel):
    code: StudyCourses
    title: str
    groups: list[StudyGroups]


COURSES: dict[StudyCourses, Course] = {
    StudyCourses.COURSE1: Course(
        code=StudyCourses.COURSE1,
        title="1 курс",
        groups=[
            StudyGroups.BKNAD251,
            StudyGroups.BKNAD252,
            StudyGroups.BKNAD253,
        ],
    ),
    StudyCourses.COURSE2: Course(
        code=StudyCourses.COURSE2,
        title="2 курс",
        groups=[
            StudyGroups.BKNAD241,
            StudyGroups.BKNAD242,
        ],
    ),
    StudyCourses.COURSE3: Course(
        code=StudyCourses.COURSE3,
        title="3 курс",
        groups=[
            StudyGroups.BKNAD231,
            StudyGroups.BKNAD232,
        ],
    ),
    StudyCourses.COURSE4: Course(
        code=StudyCourses.COURSE4,
        title="4 курс",
        groups=[
            StudyGroups.BKNAD211,
            StudyGroups.BKNAD212,
        ],
    ),
}


def get_course(code: StudyCourses) -> Course | None:
    return COURSES.get(code)


def get_courses() -> dict[StudyCourses, Course]:
    return COURSES
