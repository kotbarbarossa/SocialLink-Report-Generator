from sqlalchemy import (Column, Integer, String, MetaData,
                        Table, ForeignKey, BigInteger, Boolean)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

metadata = MetaData()
Base = declarative_base(metadata=metadata)


class User(Base):
    """
    Модель пользователя.
    Таблица БД: users
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    vk_user = relationship("VKUser", uselist=False, back_populates="user")


user_friends = Table(
    'user_friends',
    metadata,
    Column(
        'vk_user_id',
        Integer,
        ForeignKey('vk_users.id'),
        primary_key=True
        ),
    Column(
        'friend_vk_user_id',
        Integer,
        ForeignKey('vk_users.id'),
        primary_key=True
        )
)


class VKUser(Base):
    """
    Модель пользователя VK.
    Таблица БД: vk_users
    """
    __tablename__ = 'vk_users'

    id = Column(Integer, primary_key=True, index=True)
    vk_user_id = Column(BigInteger, unique=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="vk_user")
    groups = relationship(
        "VKGroup", secondary="user_groups", back_populates="users")
    friends = relationship(
        "VKUser", secondary="user_friends",
        primaryjoin="VKUser.id==user_friends.c.vk_user_id",
        secondaryjoin="VKUser.id==user_friends.c.friend_vk_user_id",
        backref="friend_users"
    )


user_groups = Table(
    'user_groups',
    Base.metadata,
    Column('vk_user_id', Integer, ForeignKey('vk_users.id')),
    Column('vk_group_id', Integer, ForeignKey('vk_groups.id'))
)


class VKGroup(Base):
    """
    Модель группы VK.
    Таблица БД: vk_groups
    """
    __tablename__ = 'vk_groups'

    id = Column(Integer, primary_key=True, index=True)
    vk_group_id = Column(BigInteger, unique=True, index=True)
    name = Column(String)
    screen_name = Column(String)
    is_closed = Column(Boolean, default=False)
    users = relationship(
        "VKUser", secondary=user_groups, back_populates="groups")
