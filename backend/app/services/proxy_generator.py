import os
import subprocess
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Tuple
from app.core.config import settings

class ProxyGenerator:
    def __init__(self, ffmpeg_bin: str = settings.ffmpeg_bin):
        self.ffmpeg_bin = ffmpeg_bin

    def generate_proxy(self, source_path: str, output_path: str, target_height: int = 720) -> Dict[str, Any]:
        source = Path(source_path)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        if not os.path.exists(source_path):
            return {
                'success': False,
                'error': f'Source file not found: {source_path}'
            }

        # A file extension is not a codec guarantee. Produce real H.264/AAC MP4,
        # atomically replacing old proxies without following an old symlink.
        temp=output.with_name(output.stem+'.encoding.mp4')
        cmd=[self.ffmpeg_bin,'-y','-v','error','-i',source_path,'-map','0:v:0','-map','0:a:0?',
             '-vf',f'scale=-2:{target_height}','-c:v','libx264','-preset','veryfast','-crf','25',
             '-threads','4','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(temp)]
        try:
            result=subprocess.run(cmd,capture_output=True,timeout=600)
            if result.returncode==0 and temp.exists():
                temp.replace(output)
                return {'success':True,'proxy_path':str(output)}
            return {'success':False,'error':result.stderr.decode('utf-8',errors='replace')}
        except Exception as exc:return {'success':False,'error':str(exc)}
        finally:temp.unlink(missing_ok=True)

    def extract_waveform_and_duration(self, video_path: str, samples: int = 200) -> Tuple[float, List[float]]:
        # Extract audio waveform peaks and duration
        duration = 15.0 # default fallback
        
        # Check duration with ffprobe or ffmpeg info
        if os.path.exists(self.ffmpeg_bin) and os.path.exists(video_path):
            try:
                cmd = [self.ffmpeg_bin, '-i', video_path]
                res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                stderr_text = res.stderr.decode('utf-8', errors='ignore')
                for line in stderr_text.splitlines():
                    if 'Duration:' in line:
                        parts = line.split('Duration:')[1].split(',')[0].strip().split(':')
                        hours = float(parts[0])
                        mins = float(parts[1])
                        secs = float(parts[2])
                        duration = hours * 3600 + mins * 60 + secs
                        break
            except Exception as e:
                print('Duration probe error:', e)

        # Measure actual audio energy. Silence stays silent; never draw invented speech.
        waveform = [0.0] * samples
        try:
            import numpy as np
            result=subprocess.run([self.ffmpeg_bin,'-v','error','-i',video_path,'-vn','-ac','1','-ar','8000','-f','s16le','pipe:1'],capture_output=True,timeout=120)
            if result.returncode==0 and result.stdout:
                audio=np.frombuffer(result.stdout,dtype='<i2').astype(np.float32)/32768
                chunks=np.array_split(audio,samples)
                peaks=np.array([float(np.sqrt(np.mean(c*c))) if len(c) else 0 for c in chunks])
                maximum=float(peaks.max())
                waveform=(peaks/maximum).round(3).tolist() if maximum>0 else waveform
        except (OSError,ValueError,subprocess.TimeoutExpired):
            pass

        return duration, waveform

proxy_generator = ProxyGenerator()
