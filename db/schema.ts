import {integer,sqliteTable,text} from 'drizzle-orm/sqlite-core';
export const topics=sqliteTable('topics',{id:text('id').primaryKey(),title:text('title').notNull(),summary:text('summary').notNull(),category:text('category').notNull(),content:text('content').notNull().default(''),public:integer('public').notNull().default(0),file:text('file'),filename:text('filename'),created:text('created').notNull()});
export const attempts=sqliteTable('attempts',{id:text('id').primaryKey(),count:integer('count').notNull(),until:integer('until').notNull()});
