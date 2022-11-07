from pytube import YouTube


def fetch_best_video_stream(yt_url):
    yt = YouTube(yt_url)
    return yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first().url


if __name__ == "__main__":
    # print(fetch_best_video_stream("https://www.youtube.com/watch?v=iJ2muJniikY"))
    pass
