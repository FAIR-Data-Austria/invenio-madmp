# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 FAIR Data Austria.
#
# Invenio-DMP is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Database models for Data Management Plans."""

import uuid
from typing import List

from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier
from invenio_rdm_records.models import BibliographicRecordDraft
from invenio_records import Record
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_utils.types import UUIDType

datamanagementplan_dataset = db.Table(
    "dmp_datamanagementplan_dataset",
    db.Column("dmp_id", UUIDType, db.ForeignKey("dmp_datamanagementplan.id")),
    db.Column("dataset_id", UUIDType, db.ForeignKey("dmp_dataset.id")),
)


class DataManagementPlan(db.Model):
    """Data Management Plan.

    Stores the external ID for the DMP, to enable querying for it in the
    DMP tool.
    """

    __tablename__ = "dmp_datamanagementplan"
    __versioned__ = {"versioning": False}

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
    """The internal identifier."""

    dmp_id = db.Column(
        db.String,
        nullable=False,
        unique=True,
    )
    """The dmp_id used to identify the DMP in the DMP tool."""

    datasets = db.relationship(
        "Dataset", secondary=datamanagementplan_dataset, back_populates="dmps"
    )

    @classmethod
    def get_by_dmp_id(cls, dmp_id: str) -> "DataManagementPlan":
        """Get the dataset with the given dmp_id."""
        return cls.query.filter(cls.dmp_id == dmp_id).one_or_none()

    @classmethod
    def get_by_record(cls, record: Record) -> List["DataManagementPlan"]:
        """Get all DMPs using the given Record in a Dataset."""
        dataset = Dataset.get_by_record(record)

        if dataset is not None:
            return dataset.dmps

        return []

    @classmethod
    def get_by_record_pid(
        cls, record_pid: PersistentIdentifier
    ) -> List["DataManagementPlan"]:
        """Get all DMPs using the Record with the given PID in a Dataset."""
        dataset = Dataset.get_by_record_pid(record_pid)

        if dataset is not None:
            return dataset.dmps

        return []

    @classmethod
    def create(
        cls,
        dmp_id: str,
        datasets: List["Dataset"] = None,
    ) -> "DataManagementPlan":
        """Create and store a DMP with the given properties."""
        dmp = None

        try:
            if not datasets:
                datasets = []
            elif isinstance(datasets, Dataset):
                # if the argument is a single Dataset, put it in a new list
                datasets = [datasets]

            with db.session.begin_nested():
                dmp = cls(
                    dmp_id=dmp_id,
                )
                dmp.datasets.extend(datasets)
                db.session.add(dmp)

        except IntegrityError:
            # TODO probably indicates a duplicate entry
            raise

        return dmp


class Dataset(db.Model):
    """Dataset as defined in a Data Management Plan.

    Stores the external ID for the dataset, to enable querying for it in the
    DMP tool.
    """

    __tablename__ = "dmp_dataset"
    __versioned__ = {"versioning": False}

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
    """The internal identifier."""

    dataset_id = db.Column(
        db.String,
        nullable=False,
        unique=True,
    )
    """The dataset_id used to identify the dataset in the DMP tool."""

    dmps = db.relationship(
        "DataManagementPlan",
        secondary=datamanagementplan_dataset,
        back_populates="datasets",
    )

    record_pid_id = db.Column(
        db.Integer,
        db.ForeignKey(PersistentIdentifier.id),
        nullable=False,
        unique=True,
    )

    record_pid = db.relationship(
        PersistentIdentifier,
        foreign_keys=[record_pid_id],
    )

    @property
    def record(self) -> Record:
        """Get the Record associated with this Dataset."""
        if self.record_pid is None:
            return None

        record = None
        record_uuid = self.record_pid.get_assigned_object()
        for api_cls in (Record, BibliographicRecordDraft):
            try:
                record = api_cls.get_record(record_uuid)
            except NoResultFound:
                continue
            else:
                # no exception means that we found a record
                break

        return record

    @classmethod
    def get_by_dataset_id(cls, dataset_id: str) -> "Dataset":
        """Get the dataset with the given dataset_id."""
        return cls.query.filter(cls.dataset_id == dataset_id).one_or_none()

    @classmethod
    def get_by_record(cls, record: Record) -> "Dataset":
        """Get the associated Dataset for the given Record."""
        # TODO: a record may have multiple PIDs, and the Dataset is only
        #       associated with one of these PIDs
        pid = PersistentIdentifier.query.filter(
            PersistentIdentifier.object_uuid == record.id
        ).first()

        if pid is None:
            return None

        return cls.get_by_record_pid(pid)

    @classmethod
    def get_by_record_pid(cls, record_pid: PersistentIdentifier) -> "Dataset":
        """Get the associated Dataset for the Record with the given PID."""
        if isinstance(record_pid, PersistentIdentifier):
            record_pid_id = record_pid.id
        else:
            record_pid_id = record_pid

        return cls.query.filter(cls.record_pid_id == record_pid_id).first()

    @classmethod
    def create(
        cls,
        dataset_id: str,
        record_pid: PersistentIdentifier,
        dmps: List[DataManagementPlan] = None,
    ) -> "Dataset":
        """Create and store a Dataset with the given properties."""
        dataset = None

        try:
            record_pid_id = record_pid
            if isinstance(record_pid, PersistentIdentifier):
                record_pid_id = record_pid.id

            if not dmps:
                dmps = []
            elif isinstance(dmps, DataManagementPlan):
                # if the argument is a single DMP, put it in a new list
                dmps = [dmps]

            with db.session.begin_nested():
                dataset = cls(
                    dataset_id=dataset_id,
                    record_pid_id=record_pid_id,
                )
                dataset.dmps.extend(dmps)
                db.session.add(dataset)

        except IntegrityError:
            # TODO probably indicates a duplicate entry
            raise

        return dataset
