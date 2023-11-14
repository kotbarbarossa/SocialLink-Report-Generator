from sqlalchemy import (Column, Integer, String, Table,
                        ForeignKey, Boolean, BigInteger, MetaData)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

metadata = MetaData()
Base = declarative_base(metadata=metadata)

user_groups = Table(
    'user_groups',
    Base.metadata,
    Column('vk_user_id', Integer, ForeignKey('vk_users.id')),
    Column('vk_group_id', Integer, ForeignKey('vk_groups.id'))
)


class VKGroup(Base):
    __tablename__ = 'vk_groups'

    id = Column(Integer, primary_key=True, index=True)
    vk_group_id = Column(BigInteger, unique=True, index=True)
    name = Column(String)
    screen_name = Column(String)
    is_closed = Column(Boolean, default=False)
    users = relationship(
        "VKUser", secondary=user_groups, back_populates="groups")
