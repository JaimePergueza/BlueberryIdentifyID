from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_micro_image_repository import (
    SqlAlchemyMicroImageRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_sample_repository import SqlAlchemySampleRepository


def test_add_get_and_list_by_sample(db_session):
    sample = SqlAlchemySampleRepository(db_session).add(Sample(sample_code="S-700"))
    repository = SqlAlchemyMicroImageRepository(db_session)
    micro_image = MicroImage(
        sample_id=sample.id,
        file_path="/storage/micro/a.jpg",
        file_name="a.jpg",
        mime_type="image/jpeg",
        file_size_bytes=1024,
        magnification="400x",
    )

    created = repository.add(micro_image)
    fetched = repository.get_by_id(created.id)
    listed = repository.list_by_sample_id(sample.id)

    assert fetched is not None
    assert fetched.magnification == "400x"
    assert len(listed) == 1
    assert listed[0].id == created.id
