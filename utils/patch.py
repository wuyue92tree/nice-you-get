import os
import sys
from you_get.common import *
from utils.logger import get_logger
from utils.exception import DownloadTreadStopException

logger = get_logger()

url = 'https://www.bilibili.com/video/BV1H64y1U7GJ?spm_id_from=333.851.b_7265636f6d6d656e64.1'

class QtSimpleProgressBar(SimpleProgressBar):
    def __init__(self, total_size, total_pieces, qt_download_thread):
        super().__init__(total_size, total_pieces=total_pieces)
        self.qt_download_thread = qt_download_thread

    def update(self):
        if self.qt_download_thread.stopFlag is True:
            raise DownloadTreadStopException('stoped')

        percent = round(self.received * 100 / self.total_size, 1)
        if percent >= 100:
            percent = 100
        self.qt_download_thread.processUpdated.emit({
            'speed': self.speed,
            'percent': percent
        })
        # logger.debug(f'try to send signer ... here {percent}')
        return super().update()


class QtPiecesProgressBar(PiecesProgressBar):
    def __init__(self, total_size, total_pieces):
        super().__init__(total_size, total_pieces=total_pieces)


def download_urls(
    urls, title, ext, total_size, output_dir='.', refer=None, merge=True,
    faker=False, headers={}, **kwargs
):
    logger.debug('Enter patched download_urls function.')
    assert urls
    if json_output:
        json_output_.download_urls(
            urls=urls, title=title, ext=ext, total_size=total_size,
            refer=refer
        )
        return
    if dry_run:
        print_user_agent(faker=faker)
        try:
            print('Real URLs:\n%s' % '\n'.join(urls))
        except:
            print('Real URLs:\n%s' % '\n'.join([j for i in urls for j in i]))
        return

    if player:
        launch_player(player, urls)
        return

    if not total_size:
        try:
            total_size = urls_size(urls, faker=faker, headers=headers)
        except:
            import traceback
            traceback.print_exc(file=sys.stdout)
            pass

    title = tr(get_filename(title))
    output_filename = get_output_filename(urls, title, ext, output_dir, merge)
    output_filepath = os.path.join(output_dir, output_filename)

    qt_download_thread = kwargs.get('qt_download_thread', False)
    force = qt_download_thread.forceReDownloadFlag

    # 媒体文件已存在，且强制下载为真时，直接删除原始文件
    if force and os.path.exists(output_filepath):
        os.remove(output_filepath)

    if total_size:
        if not force and os.path.exists(output_filepath) and not auto_rename\
                and (os.path.getsize(output_filepath) >= total_size * 0.9\
                or skip_existing_file_size_check):
            if skip_existing_file_size_check:
                log.w('Skipping %s without checking size: file already exists' % output_filepath)
            else:
                log.w('Skipping %s: file already exists' % output_filepath)
            print()
            qt_download_thread.processUpdated.emit({
                'speed': '--',
                'percent': 100,
                'isExist': True
            })
            return
        
        if qt_download_thread:
            bar = QtSimpleProgressBar(total_size, len(urls), kwargs.get('qt_download_thread'))
        else:
            bar = SimpleProgressBar(total_size, len(urls))
    else:
        if qt_download_thread:
            bar = QtPiecesProgressBar(total_size, len(urls), kwargs.get('qt_download_thread'))
        else:
            bar = PiecesProgressBar(total_size, len(urls))


    if len(urls) == 1:
        url = urls[0]
        print('Downloading %s ...' % tr(output_filename))
        bar.update()
        url_save(
            url, output_filepath, bar, refer=refer, faker=faker,
            headers=headers, **kwargs
        )
        bar.done()
    else:
        parts = []
        print('Downloading %s ...' % tr(output_filename))
        bar.update()
        for i, url in enumerate(urls):
            output_filename_i = get_output_filename(urls, title, ext, output_dir, merge, part=i)
            output_filepath_i = os.path.join(output_dir, output_filename_i)
            parts.append(output_filepath_i)
            # print 'Downloading %s [%s/%s]...' % (tr(filename), i + 1, len(urls))
            bar.update_piece(i + 1)
            url_save(
                url, output_filepath_i, bar, refer=refer, is_part=True, faker=faker,
                headers=headers, **kwargs
            )
        bar.done()

        if not merge:
            print()
            return

        if 'av' in kwargs and kwargs['av']:
            from you_get.processor.ffmpeg import has_ffmpeg_installed
            if has_ffmpeg_installed():
                from you_get.processor.ffmpeg import ffmpeg_concat_av
                ret = ffmpeg_concat_av(parts, output_filepath, ext)
                print('Merged into %s' % output_filename)
                if ret == 0:
                    for part in parts:
                        os.remove(part)

        elif ext in ['flv', 'f4v']:
            try:
                from you_get.processor.ffmpeg import has_ffmpeg_installed
                if has_ffmpeg_installed():
                    from you_get.processor.ffmpeg import ffmpeg_concat_flv_to_mp4
                    ffmpeg_concat_flv_to_mp4(parts, output_filepath)
                else:
                    from you_get.processor.join_flv import concat_flv
                    concat_flv(parts, output_filepath)
                print('Merged into %s' % output_filename)
            except:
                raise
            else:
                for part in parts:
                    os.remove(part)

        elif ext == 'mp4':
            try:
                from you_get.processor.ffmpeg import has_ffmpeg_installed
                if has_ffmpeg_installed():
                    from you_get.processor.ffmpeg import ffmpeg_concat_mp4_to_mp4
                    ffmpeg_concat_mp4_to_mp4(parts, output_filepath)
                else:
                    from you_get.processor.join_mp4 import concat_mp4
                    concat_mp4(parts, output_filepath)
                print('Merged into %s' % output_filename)
            except:
                raise
            else:
                for part in parts:
                    os.remove(part)

        elif ext == 'ts':
            try:
                from you_get.processor.ffmpeg import has_ffmpeg_installed
                if has_ffmpeg_installed():
                    from you_get.processor.ffmpeg import ffmpeg_concat_ts_to_mkv
                    ffmpeg_concat_ts_to_mkv(parts, output_filepath)
                else:
                    from you_get.processor.join_ts import concat_ts
                    concat_ts(parts, output_filepath)
                print('Merged into %s' % output_filename)
            except:
                raise
            else:
                for part in parts:
                    os.remove(part)

        elif ext == 'mp3':
            try:
                from you_get.processor.ffmpeg import has_ffmpeg_installed

                assert has_ffmpeg_installed()
                from you_get.processor.ffmpeg import ffmpeg_concat_mp3_to_mp3
                ffmpeg_concat_mp3_to_mp3(parts, output_filepath)
                print('Merged into %s' % output_filename)
            except:
                raise
            else:
                for part in parts:
                    os.remove(part)

        else:
            print("Can't merge %s files" % ext)

    print()


def monkey_patch_you_get_module(m):
    if hasattr(m, 'site'):
        Base = m.site.__class__
        class Site(Base):
            def __init__(self, *args):
                super().__init__(*args)
            
            def download(self, **kwargs):
                logger.debug('Enter patched download function.')
                if 'json_output' in kwargs and kwargs['json_output']:
                    json_output_.output(self)
                elif 'info_only' in kwargs and kwargs['info_only']:
                    if 'stream_id' in kwargs and kwargs['stream_id']:
                        # Display the stream
                        stream_id = kwargs['stream_id']
                        if 'index' not in kwargs:
                            self.p(stream_id)
                        else:
                            self.p_i(stream_id)
                    else:
                        # Display all available streams
                        if 'index' not in kwargs:
                            self.p([])
                        else:
                            stream_id = self.streams_sorted[0]['id'] if 'id' in self.streams_sorted[0] else self.streams_sorted[0]['itag']
                            self.p_i(stream_id)

                else:
                    if 'stream_id' in kwargs and kwargs['stream_id']:
                        # Download the stream
                        stream_id = kwargs['stream_id']
                    else:
                        # Download stream with the best quality
                        from you_get.processor.ffmpeg import has_ffmpeg_installed
                        if has_ffmpeg_installed() and player is None and self.dash_streams or not self.streams_sorted:
                            #stream_id = list(self.dash_streams)[-1]
                            itags = sorted(self.dash_streams,
                                        key=lambda i: -self.dash_streams[i]['size'])
                            stream_id = itags[0]
                        else:
                            stream_id = self.streams_sorted[0]['id'] if 'id' in self.streams_sorted[0] else self.streams_sorted[0]['itag']

                    if 'index' not in kwargs:
                        self.p(stream_id)
                    else:
                        self.p_i(stream_id)

                    if stream_id in self.streams:
                        urls = self.streams[stream_id]['src']
                        ext = self.streams[stream_id]['container']
                        total_size = self.streams[stream_id]['size']
                    else:
                        urls = self.dash_streams[stream_id]['src']
                        ext = self.dash_streams[stream_id]['container']
                        total_size = self.dash_streams[stream_id]['size']

                    if ext == 'm3u8' or ext == 'm4a':
                        ext = 'mp4'

                    if not urls:
                        log.wtf('[Failed] Cannot extract video source.')
                    # For legacy main()
                    headers = {}
                    if self.ua is not None:
                        headers['User-Agent'] = self.ua
                    if self.referer is not None:
                        headers['Referer'] = self.referer
                    download_urls(urls, self.title, ext, total_size, headers=headers,
                                output_dir=kwargs['output_dir'],
                                merge=kwargs['merge'],
                                av=stream_id in self.dash_streams, qt_download_thread=kwargs['qt_download_thread'])

                    if 'caption' not in kwargs or not kwargs['caption']:
                        print('Skipping captions or danmaku.')
                        return

                    for lang in self.caption_tracks:
                        filename = '%s.%s.srt' % (get_filename(self.title), lang)
                        print('Saving %s ... ' % filename, end="", flush=True)
                        srt = self.caption_tracks[lang]
                        with open(os.path.join(kwargs['output_dir'], filename),
                                'w', encoding='utf-8') as x:
                            x.write(srt)
                        print('Done.')

                    if self.danmaku is not None and not dry_run:
                        filename = '{}.cmt.xml'.format(get_filename(self.title))
                        print('Downloading {} ...\n'.format(filename))
                        with open(os.path.join(kwargs['output_dir'], filename), 'w', encoding='utf8') as fp:
                            fp.write(self.danmaku)

                    if self.lyrics is not None and not dry_run:
                        filename = '{}.lrc'.format(get_filename(self.title))
                        print('Downloading {} ...\n'.format(filename))
                        with open(os.path.join(kwargs['output_dir'], filename), 'w', encoding='utf8') as fp:
                            fp.write(self.lyrics)

                    # For main_dev()
                    #download_urls(urls, self.title, self.streams[stream_id]['container'], self.streams[stream_id]['size'])
                keep_obj = kwargs.get('keep_obj', False)
                if not keep_obj:
                    self.__init__()
        site = Site()
        m.site = site
        m.download = getattr(site, m.download.__name__)
        m.download_playlist = getattr(site, m.download_playlist.__name__)

    else:
        m.download_urls = download_urls
    return m

def any_download(url, **kwargs):
    m, url = url_to_module(url)
    m = monkey_patch_you_get_module(m)
    m.download(url, **kwargs)


def any_download_playlist(url, **kwargs):
    m, url = url_to_module(url)
    m = monkey_patch_you_get_module(m)
    m.download_playlist(url, **kwargs)
