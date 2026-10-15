import hashlib
import subprocess
import av
from app.services.proxy_generator import proxy_generator

def test_mov_proxy_is_real_h264_aac_and_does_not_overwrite_source(tmp_path):
    source=tmp_path/'upload.mov'; proxy=tmp_path/'proxy.mp4'
    subprocess.run([proxy_generator.ffmpeg_bin,'-y','-v','error','-f','lavfi','-i','color=c=blue:s=64x96:r=10','-f','lavfi','-i','sine=frequency=440:sample_rate=44100','-t','0.4','-c:v','libx264','-pix_fmt','yuv420p','-c:a','libmp3lame',str(source)],check=True,capture_output=True)
    original=hashlib.sha256(source.read_bytes()).hexdigest()
    proxy.symlink_to(source)
    result=proxy_generator.generate_proxy(str(source),str(proxy),96)
    assert result['success'] and not proxy.is_symlink()
    assert hashlib.sha256(source.read_bytes()).hexdigest()==original
    with av.open(str(proxy)) as video:
        assert video.streams.video[0].codec_context.name=='h264'
        assert video.streams.audio[0].codec_context.name=='aac'
        assert next(video.decode(video=0)).width==64
