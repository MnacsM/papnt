import os
from pathlib import Path

import click
from dotenv import load_dotenv

from .database import Database, DatabaseInfo
from .mainfunc import (add_records_from_local_pdfpath,
                       make_abbrjson_from_bibpath, make_bibfile_from_records,
                       update_unchecked_records_from_bib,
                       update_unchecked_records_from_doi,
                       update_unchecked_records_from_doi_jalc,
                       update_unchecked_records_from_uploadedpdf)
from .misc import load_config

global config, database
config = load_config(Path(__file__).parent / 'config.ini')
load_dotenv(Path(__file__).parent / '.env')
config['database']['tokenkey'] = os.getenv('TOKEN_KEY')
config['database']['database_id'] = os.getenv('DATABASE_ID')
config['misc']['dir_save_bib'] = os.getenv('DIR_SAVE_BIB')
database = Database(DatabaseInfo())


def _config_is_ok():
    tokenkey_is_empty = len(config['database']['tokenkey']) == 0
    database_id_is_empty = len(config['database']['database_id']) == 0
    if tokenkey_is_empty or database_id_is_empty:
        click.echo('Open config.ini and edit database information: '
                   f'{Path(__file__).parent / "config.ini"}', err=True)
        return False
    else:
        return True


# @click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    if ctx.invoked_subcommand is None:
        click.echo('try `papnt --help` for help')
        if _config_is_ok():
            click.echo('Your config file is in: '
                       f'{Path(__file__).parent / "config.ini"}')


@main.command()
@click.argument('paths')
def paths(paths: str):
    """Add record(s) to database by local path to PDF file"""
    if not _config_is_ok():
        return
    SEP = ','
    paths = paths.split(SEP) if SEP in paths else [paths]
    for pdfpath in paths:
        add_records_from_local_pdfpath(database, config['propnames'], pdfpath)


@main.command()
def doi():
    """Fill information in record(s) by DOI"""
    if _config_is_ok():
        update_unchecked_records_from_doi(database, config['propnames'])


@main.command()
def jalc():
    """Fill information in record(s) by DOI (JaLC API)"""
    if _config_is_ok():
        update_unchecked_records_from_doi_jalc(database, config['propnames'])


@main.command()
def bib():
    """Fill information in record(s) from bibfile"""
    if _config_is_ok():
        update_unchecked_records_from_bib(database, config['propnames'])


@main.command()
def pdf():
    """Fill information in record(s) by uploaded PDF file"""
    if _config_is_ok():
        update_unchecked_records_from_uploadedpdf(
            database, config['propnames'])


@main.command()
@click.argument('target')
def makebib(target: str):
    """Make BIB file including reference information from database"""
    if not _config_is_ok():
        return
    make_bibfile_from_records(
        database, target, config['propnames'],
        config['misc']['dir_save_bib'])
    make_abbrjson_from_bibpath(
        f'{config["misc"]["dir_save_bib"]}/{target}.bib',
        config['abbr'])


if __name__ == '__main__':
    _config_is_ok()
