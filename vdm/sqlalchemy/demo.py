'''Versioned Domain Model Support for SQLAlchemy.

TODO
====

1. How do we commit revisions (do we need to).
    * At very least do we not need to update timestamps?
    * Could have rule that flush ends revision.

1b) support for state of revision (active, deleted (spam), in-progress etc)

2. Test for revision object
'''
from datetime import datetime
import logging
logger = logging.getLogger('vdm')

from sqlalchemy import *
# from sqlalchemy import create_engine

from vdm.sqlalchemy.base import *

engine = create_engine('sqlite:///:memory:',
        # echo=True
        )
metadata = MetaData(bind=engine)


state_table = Table('state', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(8))
        )

revision_table = Table('revision', metadata,
        Column('id', Integer, primary_key=True),
        Column('timestamp', DateTime, default=datetime.now),
        Column('author', String(200)),
        Column('message', Text),
        )

## Demo tables

license_table = Table('license', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
        Column('open', Boolean),
        )

package_table = Table('package', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
        Column('title', String(100)),
        Column('license_id', Integer, ForeignKey('license.id')),
)

tag_table = Table('tag', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
)

package_tag_table = Table('package_tag', metadata,
        Column('id', Integer, primary_key=True),
        Column('package_id', Integer, ForeignKey('package.id')),
        Column('tag_id', Integer, ForeignKey('tag.id')),
        )


make_stateful(license_table)
make_stateful(package_table)
make_stateful(tag_table)
make_stateful(package_tag_table)
license_revision_table = make_revision_table(license_table)
package_revision_table = make_revision_table(package_table)
tag_revision_table = make_revision_table(tag_table)
# TODO: this has a composite primary key ...
package_tag_revision_table = make_revision_table(package_tag_table)


metadata.create_all(engine) 


## -------------------
## Mapped classes

        
class License(RevisionedObjectMixin):
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

class Package(RevisionedObjectMixin, StatefulObjectMixin):
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return '<Package %s>' % self.name

class Tag(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Tag %s>' % self.name

class PackageTag(RevisionedObjectMixin, StatefulObjectMixin):
    def __init__(self, package=None, tag=None, state=None, **kwargs):
        self.package = package
        self.tag = tag
        self.state = state
        for k,v in kwargs.items():
            setattr(self, k, v)

## --------------------------------------------------------
## Mapper Stuff

from sqlalchemy.orm import scoped_session, sessionmaker, create_session
from sqlalchemy.orm import relation, backref
# this works but other options do not ...
# Session = scoped_session(sessionmaker(autoflush=False, transactional=True))
Session = scoped_session(sessionmaker(autoflush=True, transactional=True))

mapper = Session.mapper

State = make_State(mapper, state_table)
Revision = make_Revision(mapper, revision_table)

mapper(License, license_table, properties={
    },
    extension=Revisioner(license_revision_table)
    )

mapper(Package, package_table, properties={
    'license':relation(License),
    # 'tags':relation(Tag, secondary=package_tag_table),
    'package_tags':relation(PackageTag),
    },
    extension = Revisioner(package_revision_table)
    )

mapper(Tag, tag_table)

mapper(PackageTag, package_tag_table, properties={
    'package':relation(Package),
    'tag':relation(Tag),
    },
    extension = Revisioner(package_tag_revision_table)
    )

modify_base_object_mapper(Package, Revision, State)
modify_base_object_mapper(License, Revision, State)
modify_base_object_mapper(PackageTag, Revision, State)
PackageRevision = create_object_version(mapper, Package,
        package_revision_table)
LicenseRevision = create_object_version(mapper, License,
        license_revision_table)
PackageTagRevision = create_object_version(mapper, PackageTag,
        package_tag_revision_table)

from base import add_stateful_versioned_m2m 
add_stateful_versioned_m2m(Package, PackageTag, 'tags', 'tag', 'package_tags')
add_stateful_versioned_m2m_on_version(PackageRevision, 'tags')

# need to set up the basic states for all Stateful stuff to work
import base
ACTIVE, DELETED = base.make_states(Session())

