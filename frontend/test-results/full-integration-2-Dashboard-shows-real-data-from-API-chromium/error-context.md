# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e3]:
    - generic [ref=e4]:
      - img "Aquapurite Logo" [ref=e6]
      - generic [ref=e7]: Aquapurite Private Limited's ERP
      - generic [ref=e8]: Enter your credentials to access the control panel
    - generic [ref=e9]:
      - generic [ref=e10]:
        - generic [ref=e11]:
          - generic [ref=e12]: Email
          - textbox "Email" [ref=e13]:
            - /placeholder: admin@example.com
        - generic [ref=e14]:
          - generic [ref=e15]: Password
          - textbox "Password" [ref=e16]:
            - /placeholder: ••••••••
        - button "Sign In" [ref=e17]
      - generic [ref=e18]:
        - paragraph [ref=e19]: "Demo credentials:"
        - paragraph [ref=e20]: admin@aquapurite.com / Admin@123
  - region "Notifications alt+T"
  - button "Open Next.js Dev Tools" [ref=e26] [cursor=pointer]:
    - img [ref=e27]
  - alert [ref=e30]
```