import instaloader

def get_instagram_post_links(username):
    # Create an instance of Instaloader
    L = instaloader.Instaloader()

    # Load the profile
    profile = instaloader.Profile.from_username(L.context, username)

    # Get the post URLs
    post_links = []
    for post in profile.get_posts():
        post_links.append(f"https://www.instagram.com/p/{post.shortcode}/")

    return post_links

# Example usage
if __name__ == "__main__":
    username = "instagram_username"  # Replace with the actual Instagram username
    post_links = get_instagram_post_links(username)
    for link in post_links:
        print(link)